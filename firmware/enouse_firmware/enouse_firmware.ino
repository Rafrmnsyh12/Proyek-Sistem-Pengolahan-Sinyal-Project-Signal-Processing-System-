// ARDUINO E-NOSE — FINAL + JSON FORMAT (UNO R4 WiFi)
// Adapted from Friend's Code + JSON for E-Nouse System
// Library: "Multichannel_Gas_GMXXX.h"

#include <WiFiS3.h>
#include <Wire.h>
#include "Multichannel_Gas_GMXXX.h"

// ==================== WIFI CONFIG ====================
const char* ssid = "HUPOMONE";
const char* pass = "beranak7";  
const char* RUST_IP = "192.168.100.173";  // IP PC Anda (Fixed)
const int   RUST_PORT = 8081;           // Port Backend (Fixed)
WiFiClient client;

// ==================== SENSOR ====================
GAS_GMXXX<TwoWire> gas;
#define MICS_PIN A1
float R0_mics = 100000.0;

// ==================== MOTOR PINS ====================
const int PWM_A  = 10,  DIR_A1 = 12,  DIR_A2 = 13;
const int PWM_B  = 11,  DIR_B1 = 8,   DIR_B2 = 9;

// ==================== FSM STATE ====================
enum State { IDLE, PRE_COND, RAMP_UP, HOLD, PURGE, RECOVERY, DONE };
State currentState = IDLE;
unsigned long stateTime = 0;
int currentLevel = 0;  // 0 sampai 4
const int speeds[5] = {51, 102, 153, 204, 255};
bool samplingActive = false;

// ==================== TIMING (ms) ====================
const unsigned long T_PRECOND  = 5000;
const unsigned long T_RAMP     = 2000;
const unsigned long T_HOLD     = 40000;
const unsigned long T_PURGE    = 60000;
const unsigned long T_RECOVERY = 5000;
unsigned long lastSend = 0;

// ==================== MOTOR FUNCTIONS ====================
void motorA(int speed, bool reverse = false) {
  digitalWrite(DIR_A1, reverse ? LOW : HIGH);
  digitalWrite(DIR_A2, reverse ? HIGH : LOW);
  analogWrite(PWM_A, speed);
  // Debug print untuk memastikan motor jalan
  // Serial.print("Motor A: "); Serial.println(speed);
}

void motorB(int speed, bool reverse = false) {
  digitalWrite(DIR_B1, reverse ? LOW : HIGH);
  digitalWrite(DIR_B2, reverse ? HIGH : LOW);
  analogWrite(PWM_B, speed);
}

void stopMotors() { 
  analogWrite(PWM_A, 0); 
  analogWrite(PWM_B, 0); 
}

void rampTo(int target) {
  static int cur = 0;
  if (cur < target) cur += 10;
  else if (cur > target) cur = target;
  motorA(cur);
}

// ==================== SETUP ====================
void setup() {
  Serial.begin(9600);
  
  // Setup Motor Pins
  pinMode(DIR_A1, OUTPUT); pinMode(DIR_A2, OUTPUT); pinMode(PWM_A, OUTPUT);
  pinMode(DIR_B1, OUTPUT); pinMode(DIR_B2, OUTPUT); pinMode(PWM_B, OUTPUT);
  stopMotors();

  // Setup Sensors
  Wire.begin();
  gas.begin(Wire, 0x08);

  // Connect WiFi
  Serial.print("Connecting to WiFi");
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) { 
    Serial.print("."); 
    delay(500); 
  }
  Serial.println("\nWiFi Connected!");
  Serial.println("IP: " + WiFi.localIP().toString());
  Serial.println("E-NOSE READY – Waiting for START_SAMPLING...");
}

// ==================== LOOP ====================
void loop() {
  // 1. Cek Serial Command dari GUI/User
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n'); 
    cmd.trim();
    
    Serial.print("CMD Received: "); Serial.println(cmd);
    
    if (cmd == "START_SAMPLING") startSampling();
    else if (cmd == "STOP_SAMPLING") stopSampling();
  }

  // 2. Kirim Data ke Backend setiap 250ms
  if (millis() - lastSend >= 250) { 
    lastSend = millis(); 
    sendSensorData(); 
  }
  
  // 3. Jalankan FSM Logic
  if (samplingActive) runFSM();
}

// ==================== FSM LOGIC ====================
void startSampling() { 
  if (!samplingActive) { 
    samplingActive = true; 
    currentLevel = 0; 
    changeState(PRE_COND); 
    Serial.println(">>> SAMPLING STARTED <<<");
  } 
}

void stopSampling() { 
  samplingActive = false; 
  changeState(IDLE); 
  stopMotors(); 
  Serial.println(">>> SAMPLING STOPPED <<<");
}

void changeState(State s) {
  currentState = s; 
  stateTime = millis();
  String n[] = {"IDLE","PRE_COND","RAMP_UP","HOLD","PURGE","RECOVERY","DONE"};
  Serial.println("FSM -> " + n[s] + " | Level " + String(currentLevel+1));
}

void runFSM() {
  unsigned long e = millis() - stateTime;
  switch (currentState) {
    case PRE_COND:  
      motorA(100); 
      motorB(0); 
      if (e >= T_PRECOND) changeState(RAMP_UP); 
      break;
      
    case RAMP_UP:   
      rampTo(speeds[currentLevel]); 
      if (e >= T_RAMP) changeState(HOLD); 
      break;
      
    case HOLD:      
      motorA(speeds[currentLevel]); 
      motorB(0); 
      if (e >= T_HOLD) changeState(PURGE); 
      break;
      
    case PURGE:     
      motorA(255, true); 
      motorB(255); 
      if (e >= T_PURGE) changeState(RECOVERY); 
      break;
      
    case RECOVERY:  
      stopMotors();
      if (e >= T_RECOVERY) {
        currentLevel++;
        if (currentLevel >= 5) { 
          changeState(DONE); 
          samplingActive = false; 
          Serial.println("5 LEVEL SELESAI!"); 
        }
        else {
          changeState(RAMP_UP);
        }
      }
      break;
      
    case IDLE: 
    case DONE: 
      stopMotors(); 
      break;
  }
}

// ==================== SEND DATA (JSON FORMAT) ====================
void sendSensorData() {
  // Baca Sensor GM
  uint32_t rno2 = gas.measure_NO2();
  uint32_t reth = gas.measure_C2H5OH();
  uint32_t rvoc = gas.measure_VOC();
  uint32_t rco  = gas.measure_CO();

  // Konversi nilai
  float no2 = (rno2 < 30000) ? rno2/1000.0 : -1.0;
  float eth = (reth < 30000) ? reth/1000.0 : -1.0;
  float voc = (rvoc < 30000) ? rvoc/1000.0 : -1.0;
  float co  = (rco  < 30000) ? rco /1000.0 : -1.0;

  // Baca Sensor MiCS
  float raw = analogRead(MICS_PIN) * (5.0/1023.0);
  float Rs = (raw > 0.1) ? 820.0*(5.0-raw)/raw : 100000;
  float ratio = Rs / R0_mics;
  float co_mics  = pow(10.0, (log10(ratio)-0.35)/-0.85);
  float eth_mics = pow(10.0, (log10(ratio)-0.15)/-0.65);
  float voc_mics = pow(10.0, (log10(ratio)+0.10)/-0.75);

  // Get Motor Duties (untuk monitoring)
  int motor_a_duty = 0, motor_b_duty = 0;
  if (currentState == HOLD) motor_a_duty = speeds[currentLevel];
  else if (currentState == PRE_COND) motor_a_duty = 100;
  else if (currentState == PURGE) { motor_a_duty = 255; motor_b_duty = 255; }

  // Build JSON String (Agar Backend Rust bisa baca)
  String stateNames[] = {"IDLE","PRE_COND","RAMP_UP","HOLD","PURGE","RECOVERY","DONE"};
  
  String json = "{";
  json += "\"ts\":" + String(millis()) + ",";
  json += "\"state\":\"" + stateNames[currentState] + "\",";
  json += "\"motor_A_duty\":" + String(motor_a_duty) + ",";
  json += "\"motor_B_duty\":" + String(motor_b_duty) + ",";
  json += "\"gmxxx_ch1\":" + String(rno2) + ",";
  json += "\"gmxxx_ch2\":" + String(reth) + ",";
  json += "\"gmxxx_ch3\":" + String(rvoc) + ",";
  json += "\"gmxxx_ch4\":" + String(rco) + ",";
  json += "\"mics5524_raw\":" + String((int)(raw*1000)) + ",";
  json += "\"co_mics\":" + String(co_mics, 3) + ",";
  json += "\"eth_mics\":" + String(eth_mics, 3) + ",";
  json += "\"voc_mics\":" + String(voc_mics, 3) + ",";
  json += "\"no2_gm\":" + String(no2, 3) + ",";
  json += "\"c2h5oh_gm\":" + String(eth, 3) + ",";
  json += "\"voc_gm\":" + String(voc, 3) + ",";
  json += "\"co_gm\":" + String(co, 3) + ",";
  json += "\"currentLevel\":" + String(currentLevel);
  json += "}";

  // Kirim ke Backend via WiFi TCP
  if (client.connect(RUST_IP, RUST_PORT)) {
    client.println(json);
    client.stop();
    Serial.println("Data Sent!"); // Uncomment jika ingin spam serial
  } else {
    Serial.println("Backend Connect Failed!"); 
  }
}
