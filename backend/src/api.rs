use warp::Filter;
use std::sync::Arc;
use crate::state::AppState;
use crate::db::DbClient;
use crate::file_io;
use serde::{Deserialize, Serialize};
use futures::{StreamExt, SinkExt};

#[derive(Deserialize)]
struct ConnectSerialReq {
    port: String,
}

#[derive(Deserialize)]
struct StartReq {
    label: String,
}

#[derive(Deserialize)]
struct SaveReq {
    path: String,
}

#[derive(Deserialize)]
struct SimParamsReq {
    signal1: crate::sim::SignalParams,
    signal2: crate::sim::SignalParams,
    operation: crate::sim::Operation,
}

#[derive(Serialize)]
struct ApiResponse {
    success: bool,
    message: String,
}

#[derive(Serialize)]
struct SerialPortsResponse {
    success: bool,
    ports: Vec<String>,
}

pub async fn run_api_server(port: u16, state: Arc<AppState>, db: DbClient) {
    let state_filter_state = state.clone();
    let state_filter = warp::any().map(move || state_filter_state.clone());

    // --- API ENDPOINTS ---

    // LIST SERIAL PORTS
    let list_ports_route = warp::get()
        .and(warp::path("list_serial_ports"))
        .map(|| {
            let ports = serialport::available_ports()
                .map(|ports| ports.into_iter().map(|p| p.port_name).collect())
                .unwrap_or_else(|_| Vec::new());
            warp::reply::json(&SerialPortsResponse { success: true, ports })
        });

    // CONNECT SERIAL
    let connect_serial_route = warp::post()
        .and(warp::path("connect_serial"))
        .and(warp::body::json())
        .and(state_filter.clone())
        .map(|req: ConnectSerialReq, state: Arc<AppState>| {
            let mut status = state.status.lock().unwrap();
            status.serial_port = Some(req.port.clone());
            status.serial_connected = true;
            // The serial handler loop will pick this up
            warp::reply::json(&ApiResponse { success: true, message: format!("Connecting to {}", req.port) })
        });

    // START SAMPLING
    let start_route = warp::post()
        .and(warp::path("start"))
        .and(warp::body::json())
        .and(state_filter.clone())
        .map(|req: StartReq, state: Arc<AppState>| {
            let sample_id = format!("{}_{}", req.label, chrono::Utc::now().timestamp());
            
            {
                let mut status = state.status.lock().unwrap();
                status.is_sampling = true;
                status.current_sample_id = Some(sample_id.clone());
            }
            
            // Clear buffer
            {
                let mut buffer = state.session_buffer.lock().unwrap();
                buffer.clear();
            }

            // Send command to Arduino
            let _ = state.cmd_tx.send("START_SAMPLING".to_string());
            
            state.log(format!("[INFO] ▶️ Started sampling: {}", sample_id));
            warp::reply::json(&ApiResponse { success: true, message: sample_id })
        });

    // STOP SAMPLING
    let stop_route = warp::post()
        .and(warp::path("stop"))
        .and(state_filter.clone())
        .map(|state: Arc<AppState>| {
            {
                let mut status = state.status.lock().unwrap();
                status.is_sampling = false;
                status.current_sample_id = None;
            }

            // Send command to Arduino
            let _ = state.cmd_tx.send("STOP_SAMPLING".to_string());

            state.log("[INFO] ⏹️ Stopped sampling".to_string());
            warp::reply::json(&ApiResponse { success: true, message: "Stopped".to_string() })
        });

    // SAVE CSV
    let save_csv_route = warp::post()
        .and(warp::path("save_csv"))
        .and(warp::body::json())
        .and(state_filter.clone())
        .map(|req: SaveReq, state: Arc<AppState>| {
            let buffer = state.session_buffer.lock().unwrap();
            match file_io::save_csv(&req.path, &buffer) {
                Ok(_) => {
                    state.log(format!("[INFO] 💾 Saved CSV to {}", req.path));
                    warp::reply::json(&ApiResponse { success: true, message: "Saved CSV".to_string() })
                },
                Err(e) => {
                    state.log(format!("[ERROR] Failed to save CSV: {}", e));
                    warp::reply::json(&ApiResponse { success: false, message: e.to_string() })
                }
            }
        });

    // SAVE JSON
    let save_json_route = warp::post()
        .and(warp::path("save_json"))
        .and(warp::body::json())
        .and(state_filter.clone())
        .map(|req: SaveReq, state: Arc<AppState>| {
            let buffer = state.session_buffer.lock().unwrap();
            match file_io::save_json(&req.path, &buffer) {
                Ok(_) => {
                    state.log(format!("[INFO] 💾 Saved JSON to {}", req.path));
                    warp::reply::json(&ApiResponse { success: true, message: "Saved JSON".to_string() })
                },
                Err(e) => {
                    state.log(format!("[ERROR] Failed to save JSON: {}", e));
                    warp::reply::json(&ApiResponse { success: false, message: e.to_string() })
                }
            }
        });

    // RESET
    let reset_route = warp::post()
        .and(warp::path("reset"))
        .and(state_filter.clone())
        .map(|state: Arc<AppState>| {
            {
                let mut buffer = state.session_buffer.lock().unwrap();
                buffer.clear();
            }
            state.log("[INFO] 🔄 System Reset".to_string());
            warp::reply::json(&ApiResponse { success: true, message: "Reset".to_string() })
        });

    // CONNECT INFLUXDB
    let db_clone = db.clone();
    let connect_influx_route = warp::post()
        .and(warp::path("connect_influx"))
        .and(state_filter.clone())
        .and(warp::any().map(move || db_clone.clone()))
        .then(|state: Arc<AppState>, db: DbClient| async move {
            match db.check_connection().await {
                Ok(_) => {
                    state.log("[INFO] 🗄️ InfluxDB Connected Successfully".to_string());
                    warp::reply::json(&ApiResponse { success: true, message: "Connected to InfluxDB".to_string() })
                },
                Err(e) => {
                    state.log(format!("[ERROR] ❌ InfluxDB Connection Failed: {}", e));
                    warp::reply::json(&ApiResponse { success: false, message: e.to_string() })
                }
            }
        });

    // GET SESSION DATA (For Edge Impulse Upload)
    let get_data_route = warp::get()
        .and(warp::path("session_data"))
        .and(state_filter.clone())
        .map(|state: Arc<AppState>| {
            let buffer = state.session_buffer.lock().unwrap();
            warp::reply::json(&*buffer)
        });

    // --- WEBSOCKETS ---

    // DATA STREAM
    let ws_data_route = warp::path("ws")
        .and(warp::ws())
        .and(state_filter.clone())
        .map(|ws: warp::ws::Ws, state: Arc<AppState>| {
            ws.on_upgrade(move |socket| handle_ws_data(socket, state))
        });

    // LOG STREAM
    let ws_logs_route = warp::path("logs")
        .and(warp::ws())
        .and(state_filter.clone())
        .map(|ws: warp::ws::Ws, state: Arc<AppState>| {
            ws.on_upgrade(move |socket| handle_ws_logs(socket, state))
        });

    // --- SIMULATION ENDPOINTS ---

    // START SIMULATION
    let sim_start_route = warp::post()
        .and(warp::path("sim"))
        .and(warp::path("start"))
        .and(state_filter.clone())
        .map(|state: Arc<AppState>| {
            let mut engine = state.sim_engine.lock().unwrap();
            engine.config.running = true;
            engine.start_time = std::time::Instant::now(); // Reset time on start
            state.log("[INFO] 🌊 Simulation Started".to_string());
            warp::reply::json(&ApiResponse { success: true, message: "Simulation Started".to_string() })
        });

    // STOP SIMULATION
    let sim_stop_route = warp::post()
        .and(warp::path("sim"))
        .and(warp::path("stop"))
        .and(state_filter.clone())
        .map(|state: Arc<AppState>| {
            let mut engine = state.sim_engine.lock().unwrap();
            engine.config.running = false;
            state.log("[INFO] 🛑 Simulation Stopped".to_string());
            warp::reply::json(&ApiResponse { success: true, message: "Simulation Stopped".to_string() })
        });

    // UPDATE PARAMS
    let sim_params_route = warp::post()
        .and(warp::path("sim"))
        .and(warp::path("params"))
        .and(warp::body::json())
        .and(state_filter.clone())
        .map(|req: SimParamsReq, state: Arc<AppState>| {
            let mut engine = state.sim_engine.lock().unwrap();
            engine.config.signal1 = req.signal1;
            engine.config.signal2 = req.signal2;
            engine.config.operation = req.operation;
            state.log("[INFO] ⚙️ Simulation Parameters Updated".to_string());
            warp::reply::json(&ApiResponse { success: true, message: "Params Updated".to_string() })
        });

    // SIMULATION STREAM
    let ws_sim_route = warp::path("sim")
        .and(warp::path("ws"))
        .and(warp::ws())
        .and(state_filter.clone())
        .map(|ws: warp::ws::Ws, state: Arc<AppState>| {
            ws.on_upgrade(move |socket| handle_ws_sim(socket, state))
        });

    let routes = list_ports_route
        .or(connect_serial_route)
        .or(start_route)
        .or(stop_route)
        .or(save_csv_route)
        .or(save_json_route)
        .or(reset_route)
        .or(connect_influx_route)
        .or(get_data_route)
        .or(ws_data_route)
        .or(ws_logs_route)
        .or(sim_start_route)
        .or(sim_stop_route)
        .or(sim_params_route)
        .or(ws_sim_route);

    let addr = ([0, 0, 0, 0], port);
    state.log(format!("[INFO] 🚀 API Server listening on 0.0.0.0:{}", port));
    warp::serve(routes).run(addr).await;
}

async fn handle_ws_data(ws: warp::ws::WebSocket, state: Arc<AppState>) {
    let (mut tx, _) = ws.split();
    let mut rx = state.data_tx.subscribe();

    while let Ok(data) = rx.recv().await {
        if let Ok(json) = serde_json::to_string(&data) {
            if tx.send(warp::ws::Message::text(json)).await.is_err() {
                break;
            }
        }
    }
}

async fn handle_ws_logs(ws: warp::ws::WebSocket, state: Arc<AppState>) {
    let (mut tx, _) = ws.split();
    let mut rx = state.log_tx.subscribe();

    while let Ok(msg) = rx.recv().await {
        if tx.send(warp::ws::Message::text(msg)).await.is_err() {
            break;
        }
    }
}

async fn handle_ws_sim(ws: warp::ws::WebSocket, state: Arc<AppState>) {
    let (mut tx, _) = ws.split();
    let mut rx = state.sim_tx.subscribe();

    while let Ok(data) = rx.recv().await {
        if let Ok(json) = serde_json::to_string(&data) {
            if tx.send(warp::ws::Message::text(json)).await.is_err() {
                break;
            }
        }
    }
}
