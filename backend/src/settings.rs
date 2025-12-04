use serde::Deserialize;

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct Settings {
    pub server: ServerConfig,
    pub influxdb: InfluxConfig,
    pub edge_impulse: EdgeImpulseConfig,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub arduino_port: u16,
}

#[derive(Debug, Deserialize, Clone)]
pub struct InfluxConfig {
    pub url: String,
    pub org: String,
    pub bucket: String,
    pub token: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct EdgeImpulseConfig {
    pub api_key: String,
}

impl Settings {
    pub fn new() -> Result<Self, ::config::ConfigError> {
        let builder = ::config::Config::builder()
            .add_source(::config::File::with_name("config"));
            
        builder.build()?.try_deserialize()
    }
}
