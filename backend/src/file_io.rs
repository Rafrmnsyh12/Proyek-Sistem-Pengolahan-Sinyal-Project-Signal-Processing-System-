use std::fs::File;
use std::io::Write;
use crate::state::SensorData;
use csv::Writer;

pub fn save_csv(path: &str, data: &[SensorData]) -> Result<(), Box<dyn std::error::Error>> {
    let mut wtr = Writer::from_path(path)?;
    
    // Write header handled automatically by serialize, but we might want custom headers?
    // Serde does a good job usually.
    
    for record in data {
        wtr.serialize(record)?;
    }
    
    wtr.flush()?;
    Ok(())
}

pub fn save_json(path: &str, data: &[SensorData]) -> Result<(), Box<dyn std::error::Error>> {
    let json = serde_json::to_string_pretty(data)?;
    let mut file = File::create(path)?;
    file.write_all(json.as_bytes())?;
    Ok(())
}
