mod settings;
mod state;
mod db;
mod arduino;
mod api;
mod file_io;
mod sim; 

use std::sync::Arc;
use crate::settings::Settings;
use crate::state::AppState;
use crate::db::DbClient;

#[tokio::main]
async fn main() {
    // Initialize Logger
    env_logger::init();
    println!("========================================");
    println!("🔬 E-Nouse Backend (Rust Brain) Starting...");
    println!("========================================");

    // Load Config
    let settings = match Settings::new() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("❌ Failed to load config: {}", e);
            return;
        }
    };

    println!("[INFO] ✅ Configuration loaded");
    println!("[INFO]    Arduino TCP Port: {}", settings.server.arduino_port);
    println!("[INFO]    API Port: {}", settings.server.port);

    // Initialize State
    let state = Arc::new(AppState::new(settings.clone()));

    // Initialize DB
    let db = DbClient::new(settings.influxdb.clone());

    // Spawn Arduino TCP Server
    let tcp_state = state.clone();
    let tcp_db = db.clone();
    tokio::spawn(async move {
        arduino::run_tcp_server(settings.server.arduino_port, tcp_state, tcp_db).await;
    });

    // Spawn Serial Handler
    arduino::spawn_serial_handler(state.clone());

    // Spawn Simulation Loop
    let sim_state = state.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(50)); // 20Hz
        loop {
            interval.tick().await;
            let engine = sim_state.sim_engine.lock().unwrap();
            if engine.config.running {
                let point = engine.generate_sample();
                // Broadcast
                let _ = sim_state.sim_tx.send(point);
            }
        }
    });

    // Run API Server (Main Thread)
    api::run_api_server(settings.server.port, state, db).await;
}
