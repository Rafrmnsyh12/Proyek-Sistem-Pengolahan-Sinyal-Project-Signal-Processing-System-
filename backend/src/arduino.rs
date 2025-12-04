use tokio::net::TcpListener;
use tokio::io::{AsyncBufReadExt, BufReader};
use std::sync::Arc;
use crate::state::{AppState, SensorData};
use crate::db::DbClient;
use serialport::SerialPort;
use std::time::Duration;

pub async fn run_tcp_server(port: u16, state: Arc<AppState>, db: DbClient) {
    let addr = format!("0.0.0.0:{}", port);
    let listener = match TcpListener::bind(&addr).await {
        Ok(l) => {
            state.log(format!("[INFO] 🌐 TCP Server listening on {}", addr));
            l
        },
        Err(e) => {
            state.log(format!("[ERROR] ❌ Failed to bind TCP server: {}", e));
            return;
        }
    };

    loop {
        let (mut socket, addr) = match listener.accept().await {
            Ok((s, a)) => (s, a),
            Err(e) => {
                state.log(format!("[ERROR] TCP Accept error: {}", e));
                continue;
            }
        };

        state.log(format!("[INFO] 🔌 New TCP Connection from: {}", addr));

        let state = state.clone();
        let db = db.clone();

        tokio::spawn(async move {
            let (reader, _) = socket.split();
            let mut reader = BufReader::new(reader);
            let mut line = String::new();

            loop {
                line.clear();
                match reader.read_line(&mut line).await {
                    Ok(0) => break, // EOF
                    Ok(_) => {
                        // Parse JSON
                        match serde_json::from_str::<SensorData>(&line) {
                            Ok(data) => {
                                // Log data received (Debug)
                                state.log(format!("[DEBUG] 📥 Data received: State={}, CO={}", data.state, data.co_mics));
                                
                                // Broadcast to GUI
                                let _ = state.data_tx.send(data.clone());

                                // If sampling, save to DB and Buffer
                                let is_sampling = {
                                    let status = state.status.lock().unwrap();
                                    status.is_sampling
                                };

                                if is_sampling {
                                    // Save to Buffer
                                    {
                                        let mut buffer = state.session_buffer.lock().unwrap();
                                        buffer.push(data.clone());
                                    }

                                    // Save to InfluxDB
                                    let sample_id = {
                                        let status = state.status.lock().unwrap();
                                        status.current_sample_id.clone().unwrap_or_default()
                                    };
                                    
                                    if let Err(e) = db.write_data(&data, &sample_id).await {
                                        state.log(format!("[ERROR] InfluxDB write failed: {}", e));
                                    }
                                }
                            },
                            Err(e) => {
                                state.log(format!("[WARN] Failed to parse JSON: {} | Data: {}", e, line.trim()));
                            }
                        }
                    },
                    Err(e) => {
                        state.log(format!("[ERROR] Socket read error: {}", e));
                        break;
                    }
                }
            }
        });
    }
}

pub fn spawn_serial_handler(state: Arc<AppState>) {
    tokio::spawn(async move {
        let mut rx = state.cmd_tx.subscribe();
        let mut port: Option<Box<dyn SerialPort>> = None;

        loop {
            // Check if we need to connect
            {
                let mut status = state.status.lock().unwrap();
                if status.serial_connected && port.is_none() {
                    if let Some(port_name) = &status.serial_port {
                        match serialport::new(port_name, 9600).timeout(Duration::from_millis(100)).open() {
                            Ok(p) => {
                                state.log(format!("[INFO] ✅ Serial connected to {}", port_name));
                                port = Some(p);
                            },
                            Err(e) => {
                                state.log(format!("[ERROR] ❌ Failed to open serial {}: {}", port_name, e));
                                status.serial_connected = false;
                            }
                        }
                    }
                } else if !status.serial_connected && port.is_some() {
                    state.log("[INFO] 🔌 Serial disconnected".to_string());
                    port = None;
                }
            }

            // Handle commands
            if let Ok(cmd) = rx.try_recv() {
                if let Some(p) = &mut port {
                    let cmd_str = format!("{}\n", cmd);
                    if let Err(e) = p.write_all(cmd_str.as_bytes()) {
                        state.log(format!("[ERROR] Failed to write to serial: {}", e));
                    } else {
                        state.log(format!("[INFO] 📤 Sent to Arduino: {}", cmd));
                    }
                } else {
                    state.log(format!("[WARN] Cannot send command '{}': Serial not connected", cmd));
                }
            }

            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    });
}
