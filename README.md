<<<<<<< HEAD
# Proyek-Sistem-Pengolahan-Sinyal-Project-Signal-Processing-System-
About Electronic Nouse (E-Nouse) and Combination signal.
=======
# 👃 E-Nouse: Electronic Nose System

**E-Nouse** is a comprehensive Electronic Nose system designed for real-time gas detection, visualization, and signal processing simulation. It integrates a high-performance Rust backend with a modern Python GUI to provide a robust platform for sensor monitoring and educational signal analysis.

![E-Nouse GUI](https://via.placeholder.com/800x400?text=E-Nouse+Dashboard+Placeholder)

---

## 🌟 Key Features

### 1. Real-time Sensor Monitoring
*   **Multi-Sensor Support**: Visualizes data from various gas sensors (CO, Ethanol, VOC, NO2) and motor states.
*   **High-Speed Plotting**: Uses `pyqtgraph` for smooth, high-frequency real-time graphing.
*   **Data Logging**: Automatically logs sensor data to **InfluxDB** for historical analysis.

### 2. Signal Combination Simulation
*   **Educational Tool**: A dedicated tab for simulating and combining signals.
*   **Signal Generation**: Generate two independent sine waves ($A \sin(2\pi f t + \phi)$).
*   **Mathematical Operations**: Combine signals using Addition (+), Subtraction (-), or Multiplication (*).
*   **Real-time Visualization**: See the individual signals and the resulting waveform instantly.
*   **Export**: Save simulation results to **CSV** or **JSON**.

### 3. Robust Architecture
*   **Backend**: Built with **Rust** (`tokio`, `warp`) for concurrency, safety, and speed.
*   **Frontend**: Built with **Python** (`PySide6`) for a professional and responsive user interface.
*   **Communication**: Uses **WebSockets** for low-latency data streaming and **HTTP REST API** for control.

---

## 🛠️ Tech Stack

*   **Backend**: Rust 🦀
    *   `tokio`: Async runtime.
    *   `warp`: Web server (API & WebSockets).
    *   `serialport`: Hardware communication.
*   **Frontend**: Python 🐍
    *   `PySide6` (Qt): GUI Framework.
    *   `pyqtgraph`: Real-time plotting.
*   **Database**: InfluxDB 🗄️
*   **Hardware**: Arduino (Firmware in C++).

---

## 🚀 Installation & Setup

### Prerequisites
1.  **Rust**: Install via [rustup.rs](https://rustup.rs/).
2.  **Python 3.10+**: Install from [python.org](https://www.python.org/).
3.  **InfluxDB**: Install and run InfluxDB v2.
4.  **Arduino**: Connect your E-Nouse hardware via USB.

### 1. Backend Setup
```bash
cd backend
# Build and Run
cargo run
```
*The backend will start the API server at `http://localhost:3000` and listen for Arduino on port `8081`.*

### 2. Frontend Setup
```bash
cd gui
# Install dependencies
pip install -r requirements.txt
# Run the GUI
python main.py
```

---

## 📖 Usage Guide

### E-Nouse Visualizer Tab
1.  **Connect Serial**: Select the Arduino COM port and click "Connect".
2.  **Start Sampling**: Click "Start" to begin recording and streaming sensor data.
3.  **Stop**: Click "Stop" to pause.
4.  **Save**: Use "Save CSV" or "Save JSON" to export the session data.

### Signal Simulation Tab
1.  **Configure Signals**: Set Amplitude, Frequency, and Phase for Signal 1 (Blue) and Signal 2 (Green).
2.  **Select Operation**: Choose Add, Subtract, or Multiply.
3.  **Start Simulation**: Click "Start Sim" to generate waves.
4.  **Update**: Change parameters and click "Update Params" to see changes in real-time.
5.  **Export**: Click "Save CSV" or "Save JSON" to save the simulation data.

---

## 📂 Project Structure

```
Proyek_SPS_ENose/
├── backend/                # Rust Backend
│   ├── src/                # Source code (main.rs, api.rs, sim.rs, etc.)
│   └── Cargo.toml          # Rust dependencies
├── gui/                    # Python Frontend
│   ├── main.py             # Main GUI application
│   └── requirements.txt    # Python dependencies
├── firmware/               # Arduino Firmware
│   └── enouse_firmware/    # .ino files
└── README.md               # This file
```

---

## 🤝 Contributing
Feel free to fork this repository and submit Pull Requests.

---

*Developed for Signal Processing System Course.*
>>>>>>> 725f948 (Project Electronic Nouse)
