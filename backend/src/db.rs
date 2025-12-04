use influxdb2::Client;
use influxdb2::models::DataPoint;
use crate::state::SensorData;
use crate::settings::InfluxConfig;

#[derive(Clone)]
pub struct DbClient {
    client: Client,
    bucket: String,
    #[allow(dead_code)]
    org: String,
}

impl DbClient {
    pub fn new(config: InfluxConfig) -> Self {
        let client = Client::new(config.url, config.org.clone(), config.token);
        Self {
            client,
            bucket: config.bucket,
            org: config.org,
        }
    }

    pub async fn write_data(&self, data: &SensorData, sample_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        let points = vec![
            DataPoint::builder("sensors")
                .tag("sample_id", sample_id)
                .tag("state", &data.state)
                .field("co_mics", data.co_mics as f64)
                .field("eth_mics", data.eth_mics as f64)
                .field("voc_mics", data.voc_mics as f64)
                .field("no2_gm", data.no2_gm as f64)
                .field("c2h5oh_gm", data.c2h5oh_gm as f64)
                .field("voc_gm", data.voc_gm as f64)
                .field("co_gm", data.co_gm as f64)
                .field("motor_A", data.motor_a_duty as i64)
                .field("motor_B", data.motor_b_duty as i64)
                .build()?,
        ];

        self.client.write(&self.bucket, futures::stream::iter(points)).await?;
        Ok(())
    }

    pub async fn check_connection(&self) -> Result<(), Box<dyn std::error::Error>> {
        // Try to list buckets to verify connection and auth
        self.client.list_buckets(None).await?;
        Ok(())
    }
}
