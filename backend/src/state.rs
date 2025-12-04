use serde::{Deserialize, Serialize};
use tokio::sync::broadcast;
use std::sync::{Arc, Mutex};
use crate::settings::Settings;
use crate::sim::{SimEngine, SimDataPoint};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensorData {
    pub ts: u64,
    pub state: String,
    #[serde(rename = "motor_A_duty")]
    pub motor_a_duty: i32,
    #[serde(rename = "motor_B_duty")]
    pub motor_b_duty: i32,
    pub gmxxx_ch1: u32,
    pub gmxxx_ch2: u32,
    pub gmxxx_ch3: u32,
    pub gmxxx_ch4: u32,
    pub mics5524_raw: u32,
    pub co_mics: f32,
    pub eth_mics: f32,
    pub voc_mics: f32,
    pub no2_gm: f32,
    pub c2h5oh_gm: f32,
    pub voc_gm: f32,
    pub co_gm: f32,
    #[serde(rename = "currentLevel")]
    pub current_level: i32,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Status {
    pub is_sampling: bool,
    pub current_sample_id: Option<String>,
    pub mode: String, // "real" or "simulation"
    pub serial_connected: bool,
    pub serial_port: Option<String>,
}

pub struct AppState {
    pub status: Arc<Mutex<Status>>,
    pub data_tx: broadcast::Sender<SensorData>,
    pub log_tx: broadcast::Sender<String>,
    pub cmd_tx: broadcast::Sender<String>, // To send commands to Serial thread
    pub sim_tx: broadcast::Sender<SimDataPoint>, // NEW: Sim Data Channel
    pub session_buffer: Arc<Mutex<Vec<SensorData>>>,
    pub sim_engine: Arc<Mutex<SimEngine>>, 
    #[allow(dead_code)]
    pub settings: Settings,
}

impl AppState {
    pub fn new(settings: Settings) -> Self {
        let (data_tx, _) = broadcast::channel(100);
        let (log_tx, _) = broadcast::channel(100);
        let (cmd_tx, _) = broadcast::channel(100);
        let (sim_tx, _) = broadcast::channel(100); // NEW

        Self {
            status: Arc::new(Mutex::new(Status {
                is_sampling: false,
                current_sample_id: None,
                mode: "real".to_string(),
                serial_connected: false,
                serial_port: None,
            })),
            data_tx,
            log_tx,
            cmd_tx,
            sim_tx,
            session_buffer: Arc::new(Mutex::new(Vec::new())),
            sim_engine: Arc::new(Mutex::new(SimEngine::new())), 
            settings,
        }
    }

    pub fn log(&self, message: String) {
        // Print to terminal
        println!("{}", message);
        // Broadcast to GUI
        let _ = self.log_tx.send(message);
    }
}
