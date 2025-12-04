use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignalParams {
    pub amplitude: f64,
    pub frequency: f64,
    pub phase: f64, // in degrees
}
//test
impl Default for SignalParams {
    fn default() -> Self {
        Self {
            amplitude: 1.0,
            frequency: 1.0,
            phase: 0.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Operation {
    Add,
    Subtract,
    Multiply,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimConfig {
    pub signal1: SignalParams,
    pub signal2: SignalParams,
    pub operation: Operation,
    pub running: bool,
}

impl Default for SimConfig {
    fn default() -> Self {
        Self {
            signal1: SignalParams::default(),
            signal2: SignalParams::default(),
            operation: Operation::Add,
            running: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimDataPoint {
    pub time: f64,
    pub x1: f64,
    pub x2: f64,
    pub y: f64,
}

pub struct SimEngine {
    pub config: SimConfig,
    pub start_time: std::time::Instant,
}

impl SimEngine {
    pub fn new() -> Self {
        Self {
            config: SimConfig::default(),
            start_time: std::time::Instant::now(),
        }
    }

    pub fn generate_sample(&self) -> SimDataPoint {
        let t = self.start_time.elapsed().as_secs_f64();
        
        let s1 = &self.config.signal1;
        let s2 = &self.config.signal2;

        // x(t) = A * sin(2 * pi * f * t + phi_rad)
        let phi1_rad = s1.phase.to_radians();
        let phi2_rad = s2.phase.to_radians();

        let x1 = s1.amplitude * (2.0 * PI * s1.frequency * t + phi1_rad).sin();
        let x2 = s2.amplitude * (2.0 * PI * s2.frequency * t + phi2_rad).sin();

        let y = match self.config.operation {
            Operation::Add => x1 + x2,
            Operation::Subtract => x1 - x2,
            Operation::Multiply => x1 * x2,
        };

        SimDataPoint { time: t, x1, x2, y }
    }
}
