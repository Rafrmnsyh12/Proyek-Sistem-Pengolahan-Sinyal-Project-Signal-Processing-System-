import sys
import requests
import pyqtgraph as pg
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QMessageBox, QComboBox, QTextEdit, QFileDialog, QCheckBox, QDoubleSpinBox,
                               QGroupBox, QFormLayout, QTabWidget)
from PySide6.QtCore import Slot, QTimer, QThread, Signal
from PySide6.QtGui import QTextCursor
import websocket
import json
import threading
from datetime import datetime

API_URL = "http://localhost:3000"
WS_URL = "ws://localhost:3000/ws"
WS_LOG_URL = "ws://localhost:3000/logs"
WS_SIM_URL = "ws://localhost:3000/sim/ws"

# Edge Impulse Configuration
EDGE_IMPULSE_API_KEY = "ei_22521a805fc50af48c92c34c52aadac76507b2728ee7a0e2"
EDGE_IMPULSE_URL = "https://ingestion.edgeimpulse.com/api/training/data"

class WebSocketWorker(QThread):
    data_received = Signal(dict)
    log_received = Signal(str)
    
    def __init__(self, url, is_log=False):
        super().__init__()
        self.url = url
        self.is_log = is_log
        self.running = True
        self.ws = None

    def run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(self.url,
                                               on_message=self.on_message,
                                               on_error=self.on_error)
                self.ws.run_forever()
                QThread.sleep(1) # Reconnect delay
            except Exception:
                QThread.sleep(1)

    def on_message(self, ws, message):
        if self.is_log:
            self.log_received.emit(message)
        else:
            try:
                data = json.loads(message)
                self.data_received.emit(data)
            except:
                pass

    def on_error(self, ws, error):
        pass

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

class ENouseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # --- Header ---
        header = QLabel("🔬 E-NOSE VISUALIZER")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #4FC3F7; padding: 10px;")
        self.layout.addWidget(header)

        # --- Status Bar ---
        info_layout = QHBoxLayout()
        self.state_label = QLabel("🔄 State: IDLE")
        self.state_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info_layout.addWidget(self.state_label)
        info_layout.addStretch()
        self.layout.addLayout(info_layout)

        # --- Graph Controls ---
        graph_ctrl_layout = QHBoxLayout()
        graph_ctrl_layout.addWidget(QLabel("↕️ Spacing:"))
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(0, 10000)
        self.spin_spacing.setValue(100.0)
        self.spin_spacing.setSingleStep(10.0)
        self.spin_spacing.setStyleSheet("background: #1e1e2e; color: #4FC3F7; font-weight: bold;")
        graph_ctrl_layout.addWidget(self.spin_spacing)

        btn_auto_space = QPushButton("✨ Auto-Space")
        btn_auto_space.clicked.connect(self.auto_spacing)
        btn_auto_space.setStyleSheet("background: #00E676; color: black; font-weight: bold;")
        graph_ctrl_layout.addWidget(btn_auto_space)

        graph_ctrl_layout.addWidget(QLabel("⚡ Gain:"))
        self.spin_gain = QDoubleSpinBox()
        self.spin_gain.setRange(0.1, 1000)
        self.spin_gain.setValue(1.0)
        self.spin_gain.setSingleStep(0.1)
        self.spin_gain.setStyleSheet("background: #1e1e2e; color: #69F0AE; font-weight: bold;")
        graph_ctrl_layout.addWidget(self.spin_gain)
        graph_ctrl_layout.addStretch()
        self.layout.addLayout(graph_ctrl_layout)

        # --- Graph ---
        self.plot_widget = pg.PlotWidget(title="Real-time Sensor Data")
        self.plot_widget.setBackground('#000000')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.layout.addWidget(self.plot_widget)

        # --- Data Structures ---
        self.curves = {}
        self.data_buffer = {
            "co_mics": [], "eth_mics": [], "voc_mics": [],
            "no2_gm": [], "c2h5oh_gm": [], "voc_gm": [], "co_gm": []
        }
        self.timestamps = []
        self.start_time = 0
        self.channels = [
            ("co_mics", "CO (MiCS)", "CO (M)", "#FF5252"),
            ("eth_mics", "Ethanol (MiCS)", "Eth (M)", "#448AFF"),
            ("voc_mics", "VOC (MiCS)", "VOC (M)", "#69F0AE"),
            ("no2_gm", " NO₂ (GM)", "NO₂ (G)", "#FFEB3B"),
            ("c2h5oh_gm", "Ethanol (GM)", "Eth (G)", "#E040FB"),
            ("voc_gm", "VOC (GM)", "VOC (G)", "#FFAB40"),
            ("co_gm", "CO (GM)", "CO (G)", "#FFFFFF")
        ]

        for i, (key, label, short_label, color) in enumerate(self.channels):
            curve = self.plot_widget.plot(pen=pg.mkPen(color, width=2), name=label)
            self.curves[key] = curve

        # --- Controls ---
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("📡 Serial:"))
        self.serial_combo = QComboBox()
        self.serial_combo.addItem("-- Refreshing --")
        ctrl_layout.addWidget(self.serial_combo)
        
        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedWidth(40)
        btn_refresh.clicked.connect(self.refresh_ports)
        ctrl_layout.addWidget(btn_refresh)

        btn_connect = QPushButton("🔗 Connect")
        btn_connect.clicked.connect(self.connect_serial)
        ctrl_layout.addWidget(btn_connect)

        ctrl_layout.addWidget(QLabel("🏷️ Label:"))
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("test_sample")
        ctrl_layout.addWidget(self.label_input)

        btn_start = QPushButton("▶️ Start")
        btn_start.clicked.connect(self.start_sampling)
        ctrl_layout.addWidget(btn_start)

        btn_stop = QPushButton("⏹️ Stop")
        btn_stop.clicked.connect(self.stop_sampling)
        ctrl_layout.addWidget(btn_stop)

        btn_reset = QPushButton("🔄 Reset")
        btn_reset.clicked.connect(self.reset_system)
        ctrl_layout.addWidget(btn_reset)
        self.layout.addLayout(ctrl_layout)

        # --- Save & Export ---
        file_layout = QHBoxLayout()
        btn_save_csv = QPushButton("💾 Save CSV")
        btn_save_csv.clicked.connect(self.save_csv)
        file_layout.addWidget(btn_save_csv)

        btn_save_json = QPushButton("💾 Save JSON")
        btn_save_json.clicked.connect(self.save_json)
        file_layout.addWidget(btn_save_json)

        btn_upload = QPushButton("☁️ Upload Edge Impulse")
        btn_upload.clicked.connect(self.upload_edge_impulse)
        file_layout.addWidget(btn_upload)

        btn_influx = QPushButton("🗄️ Connect InfluxDB")
        btn_influx.clicked.connect(self.connect_influx)
        file_layout.addWidget(btn_influx)

        btn_gnuplot = QPushButton("💾 Save GNUplot")
        btn_gnuplot.clicked.connect(self.save_gnuplot)
        btn_gnuplot.setStyleSheet("background: #FF9800; color: black;")
        file_layout.addWidget(btn_gnuplot)

        file_layout.addStretch()
        self.layout.addLayout(file_layout)

        # --- Log Panel ---
        self.layout.addWidget(QLabel("📋 Backend Logs:"))
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)
        self.log_display.setStyleSheet("font-family: Consolas; font-size: 11px; background: #0a0a14;")
        self.layout.addWidget(self.log_display)

        # Initial refresh
        QTimer.singleShot(1000, self.refresh_ports)

    # ... (Keep all methods: refresh_ports, connect_serial, start_sampling, etc.)
    
    def refresh_ports(self):
        try:
            res = requests.get(f"{API_URL}/list_serial_ports")
            if res.status_code == 200:
                ports = res.json().get('ports', [])
                self.serial_combo.clear()
                if ports:
                    self.serial_combo.addItems(ports)
                else:
                    self.serial_combo.addItem("-- No Ports --")
        except:
            pass

    def connect_serial(self):
        port = self.serial_combo.currentText()
        if "--" in port: return
        try:
            requests.post(f"{API_URL}/connect_serial", json={"port": port})
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def start_sampling(self):
        label = self.label_input.text() or "test"
        try:
            requests.post(f"{API_URL}/start", json={"label": label})
            self.timestamps = []
            for k in self.data_buffer: self.data_buffer[k] = []
            for curve in self.curves.values(): curve.setData([], [])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def stop_sampling(self):
        try:
            requests.post(f"{API_URL}/stop")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def reset_system(self):
        try:
            requests.post(f"{API_URL}/reset")
            self.timestamps = []
            for k in self.data_buffer: self.data_buffer[k] = []
            for curve in self.curves.values(): curve.setData([], [])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                requests.post(f"{API_URL}/save_csv", json={"path": path})
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON Files (*.json)")
        if path:
            try:
                requests.post(f"{API_URL}/save_json", json={"path": path})
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def connect_influx(self):
        try:
            res = requests.post(f"{API_URL}/connect_influx")
            if res.status_code == 200:
                data = res.json()
                if data['success']:
                    QMessageBox.information(self, "Success", data['message'])
                else:
                    QMessageBox.critical(self, "Error", data['message'])
            else:
                QMessageBox.critical(self, "Error", f"HTTP {res.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def upload_edge_impulse(self):
        try:
            res = requests.get(f"{API_URL}/session_data")
            if res.status_code != 200:
                QMessageBox.warning(self, "Error", "Failed to fetch data from backend")
                return
            
            data = res.json()
            if not data:
                QMessageBox.warning(self, "Empty", "No data to upload")
                return

            values = []
            for row in data:
                values.append([
                    row.get('co_mics', 0),
                    row.get('eth_mics', 0),
                    row.get('voc_mics', 0),
                    row.get('no2_gm', 0),
                    row.get('c2h5oh_gm', 0),
                    row.get('voc_gm', 0),
                    row.get('co_gm', 0),
                ])

            payload = {
                "protected": {
                    "ver": "v1",
                    "alg": "HS256",
                    "iat": int(datetime.now().timestamp() * 1000)
                },
                "signature": "signature_placeholder",
                "payload": {
                    "device_name": "e-nouse",
                    "device_type": "ENOSE",
                    "interval_ms": 250,
                    "sensors": [
                        {"name": "co_mics", "units": "ppm"},
                        {"name": "eth_mics", "units": "ppm"},
                        {"name": "voc_mics", "units": "ppm"},
                        {"name": "no2_gm", "units": "ppm"},
                        {"name": "c2h5oh_gm", "units": "ppm"},
                        {"name": "voc_gm", "units": "ppm"},
                        {"name": "co_gm", "units": "ppm"}
                    ],
                    "values": values
                }
            }

            filename = f"sample_{int(datetime.now().timestamp())}.json"
            label = self.label_input.text() or "unknown"
            
            ei_res = requests.post(
                EDGE_IMPULSE_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": EDGE_IMPULSE_API_KEY,
                    "x-file-name": filename,
                    "x-label": label
                },
                json=payload
            )
            
            if ei_res.status_code == 200:
                QMessageBox.information(self, "Success", f"Uploaded {len(values)} samples to Edge Impulse!")
            else:
                QMessageBox.critical(self, "Upload Failed", ei_res.text)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_gnuplot(self):
        if not self.timestamps:
            QMessageBox.warning(self, "Warning", "No data to save!")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save GNUplot Data", "", "Data Files (*.dat)")
        if not path: return

        try:
            import os
            base_name = os.path.splitext(path)[0]
            dat_file = f"{base_name}.dat"
            gp_file = f"{base_name}.gp"
            
            # 1. Save Data to .dat file
            with open(dat_file, 'w', encoding='utf-8') as f:
                # Header
                headers = ["Time"] + [c[2] for c in self.channels] # Use short labels
                f.write("# " + " ".join(headers).replace(" ", "_") + "\n")
                
                # Data
                # Ensure all buffers have same length as timestamps
                min_len = len(self.timestamps)
                for k in self.data_buffer:
                    min_len = min(min_len, len(self.data_buffer[k]))
                
                for i in range(min_len):
                    row = [f"{self.timestamps[i]:.4f}"]
                    for k, _, _, _ in self.channels:
                        val = self.data_buffer[k][i] if i < len(self.data_buffer[k]) else 0
                        row.append(f"{val:.4f}")
                    f.write(" ".join(row) + "\n")
            
            # 2. Create GNUplot Script .gp
            with open(gp_file, 'w', encoding='utf-8') as f:
                plot_cmds = []
                for i, (_, _, label, color) in enumerate(self.channels):
                    # Column 1 is Time, so data starts at Column 2
                    col_idx = i + 2
                    plot_cmds.append(f'"{os.path.basename(dat_file)}" using 1:{col_idx} with lines title "{label}" lc rgb "{color}" lw 2')
                
                plot_cmd_str = ", \\\n     ".join(plot_cmds)

                f.write(f"""
set title "E-Nouse Data: {os.path.basename(base_name)}"
set xlabel "Time (s)"
set ylabel "Sensor Value"
set grid
set key outside
set term wxt size 1000,600 persist
plot {plot_cmd_str}
pause mouse close
""")
            
            QMessageBox.information(self, "Success", f"Saved:\n{dat_file}\n{gp_file}\n\nYou can run it with: gnuplot {os.path.basename(gp_file)}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save GNUplot files: {str(e)}")


    @Slot(dict)
    def update_graph(self, data):
        co_val = data.get('co_mics', 0)
        self.state_label.setText(f"🔄 State: {data.get('state', 'UNKNOWN')} | CO (MiCS): {co_val:.4f}")
        
        current_time = datetime.now().timestamp()
        if not self.timestamps:
            self.start_time = current_time
            rel_time = 0
        else:
            rel_time = current_time - self.start_time
        
        self.timestamps.append(rel_time)
        if len(self.timestamps) > 10000: self.timestamps.pop(0)

        spacing = self.spin_spacing.value()
        gain = self.spin_gain.value()

        for i, (key, _, _, _) in enumerate(self.channels):
            val = data.get(key, 0)
            self.data_buffer[key].append(val)
            if len(self.data_buffer[key]) > 10000: 
                self.data_buffer[key].pop(0)
            
            if self.data_buffer[key]:
                baseline = min(self.data_buffer[key])
            else:
                baseline = 0
            
            offset = (len(self.channels) - 1 - i) * spacing
            display_data = [((v - baseline) * gain) + offset for v in self.data_buffer[key]]
            self.curves[key].setData(self.timestamps, display_data)

    @Slot()
    def auto_spacing(self):
        max_amplitude = 0
        for key in self.data_buffer:
            if self.data_buffer[key]:
                amp = max(self.data_buffer[key]) - min(self.data_buffer[key])
                if amp > max_amplitude:
                    max_amplitude = amp
        
        if max_amplitude > 0:
            gain = self.spin_gain.value()
            new_spacing = max_amplitude * gain * 1.2
            self.spin_spacing.setValue(new_spacing)
            self.update_log(f"Auto-Spacing set to: {new_spacing:.2f}")

    @Slot(str)
    def update_log(self, message):
        self.log_display.append(f"<span style='color:#ccc'>{message}</span>")
        self.log_display.moveCursor(QTextCursor.End)


class SimulationTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # --- Header ---
        header = QLabel("📈 SIGNAL COMBINATION SIMULATION")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #E040FB; padding: 10px;")
        self.layout.addWidget(header)

        # --- Controls Area ---
        ctrl_layout = QHBoxLayout()
        
        # Signal 1 Group
        grp_s1 = QGroupBox("Signal 1 (Blue)")
        grp_s1.setStyleSheet("QGroupBox { border: 1px solid #448AFF; margin-top: 10px; } QGroupBox::title { color: #448AFF; }")
        l1 = QFormLayout()
        self.s1_amp = QDoubleSpinBox(); self.s1_amp.setValue(1.0); self.s1_amp.setRange(0, 100)
        self.s1_freq = QDoubleSpinBox(); self.s1_freq.setValue(1.0); self.s1_freq.setRange(0, 100)
        self.s1_phase = QDoubleSpinBox(); self.s1_phase.setValue(0.0); self.s1_phase.setRange(0, 360)
        l1.addRow("Amplitude:", self.s1_amp)
        l1.addRow("Frequency (Hz):", self.s1_freq)
        l1.addRow("Phase (°):", self.s1_phase)
        grp_s1.setLayout(l1)
        ctrl_layout.addWidget(grp_s1)

        # Operation
        op_layout = QVBoxLayout()
        op_layout.addWidget(QLabel("Operation:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(["Add (+)", "Subtract (-)", "Multiply (*)"])
        op_layout.addWidget(self.op_combo)
        ctrl_layout.addLayout(op_layout)

        # Signal 2 Group
        grp_s2 = QGroupBox("Signal 2 (Green)")
        grp_s2.setStyleSheet("QGroupBox { border: 1px solid #69F0AE; margin-top: 10px; } QGroupBox::title { color: #69F0AE; }")
        l2 = QFormLayout()
        self.s2_amp = QDoubleSpinBox(); self.s2_amp.setValue(1.0); self.s2_amp.setRange(0, 100)
        self.s2_freq = QDoubleSpinBox(); self.s2_freq.setValue(2.0); self.s2_freq.setRange(0, 100)
        self.s2_phase = QDoubleSpinBox(); self.s2_phase.setValue(0.0); self.s2_phase.setRange(0, 360)
        l2.addRow("Amplitude:", self.s2_amp)
        l2.addRow("Frequency (Hz):", self.s2_freq)
        l2.addRow("Phase (°):", self.s2_phase)
        grp_s2.setLayout(l2)
        ctrl_layout.addWidget(grp_s2)

        self.layout.addLayout(ctrl_layout)

        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        btn_update = QPushButton("⚙️ Update Params")
        btn_update.clicked.connect(self.update_params)
        btn_layout.addWidget(btn_update)

        btn_start = QPushButton("▶️ Start Sim")
        btn_start.clicked.connect(self.start_sim)
        btn_start.setStyleSheet("background: #00E676; color: black;")
        btn_layout.addWidget(btn_start)

        btn_stop = QPushButton("⏹️ Stop Sim")
        btn_stop.clicked.connect(self.stop_sim)
        btn_stop.setStyleSheet("background: #FF5252; color: white;")
        btn_layout.addWidget(btn_stop)
        self.layout.addLayout(btn_layout)

        # --- Save Buttons ---
        save_layout = QHBoxLayout()
        btn_save_csv = QPushButton("💾 Save CSV")
        btn_save_csv.clicked.connect(self.save_csv)
        save_layout.addWidget(btn_save_csv)

        btn_save_json = QPushButton("💾 Save JSON")
        btn_save_json.clicked.connect(self.save_json)
        save_layout.addWidget(btn_save_json)
        
        self.layout.addLayout(save_layout)

        # --- Plots ---
        # We use 3 separate plots for clarity as requested
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('#000000')
        self.layout.addWidget(self.plot_layout)

        # Plot 1: Signal 1
        self.p1 = self.plot_layout.addPlot(row=0, col=0, title="Signal 1")
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        self.curve1 = self.p1.plot(pen=pg.mkPen('#448AFF', width=2))

        # Plot 2: Signal 2
        self.p2 = self.plot_layout.addPlot(row=1, col=0, title="Signal 2")
        self.p2.showGrid(x=True, y=True, alpha=0.3)
        self.curve2 = self.p2.plot(pen=pg.mkPen('#69F0AE', width=2))
        self.p2.setXLink(self.p1)

        # Plot 3: Result
        self.p3 = self.plot_layout.addPlot(row=2, col=0, title="Result")
        self.p3.showGrid(x=True, y=True, alpha=0.3)
        self.curve3 = self.p3.plot(pen=pg.mkPen('#E040FB', width=2))
        self.p3.setXLink(self.p1)

        # Data Buffers
        self.times = []
        self.data1 = []
        self.data2 = []
        self.data3 = []

    def update_params(self):
        op_map = {0: "Add", 1: "Subtract", 2: "Multiply"}
        payload = {
            "signal1": {
                "amplitude": self.s1_amp.value(),
                "frequency": self.s1_freq.value(),
                "phase": self.s1_phase.value()
            },
            "signal2": {
                "amplitude": self.s2_amp.value(),
                "frequency": self.s2_freq.value(),
                "phase": self.s2_phase.value()
            },
            "operation": op_map[self.op_combo.currentIndex()]
        }
        try:
            requests.post(f"{API_URL}/sim/params", json=payload)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def start_sim(self):
        try:
            requests.post(f"{API_URL}/sim/start")
            self.times = []
            self.data1 = []
            self.data2 = []
            self.data3 = []
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def stop_sim(self):
        try:
            requests.post(f"{API_URL}/sim/stop")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Simulation CSV", "", "CSV Files (*.csv)")
        if not path: return
        try:
            import csv
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Signal1", "Signal2", "Result"])
                for i in range(len(self.times)):
                    writer.writerow([self.times[i], self.data1[i], self.data2[i], self.data3[i]])
            QMessageBox.information(self, "Success", f"Saved {len(self.times)} points to CSV")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Simulation JSON", "", "JSON Files (*.json)")
        if not path: return
        try:
            data = []
            for i in range(len(self.times)):
                data.append({
                    "time": self.times[i],
                    "signal1": self.data1[i],
                    "signal2": self.data2[i],
                    "result": self.data3[i]
                })
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Success", f"Saved {len(self.times)} points to JSON")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


    @Slot(dict)
    def update_graph(self, data):
        # data = {time, x1, x2, y}
        t = data.get('time', 0)
        self.times.append(t)
        self.data1.append(data.get('x1', 0))
        self.data2.append(data.get('x2', 0))
        self.data3.append(data.get('y', 0))

        if len(self.times) > 500:
            self.times.pop(0)
            self.data1.pop(0)
            self.data2.pop(0)
            self.data3.pop(0)

        self.curve1.setData(self.times, self.data1)
        self.curve2.setData(self.times, self.data2)
        self.curve3.setData(self.times, self.data3)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔬 E-Nouse System - Visualizer")
        self.resize(1400, 900)
        
        pg.setConfigOptions(antialias=True)
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow { background: #0f0f1e; }
            QWidget { color: #e8e8e8; font-family: 'Segoe UI'; font-size: 13px; }
            QLabel { color: #f0f0f0; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4FC3F7, stop:1 #0288D1);
                color: white; border: none; border-radius: 8px;
                padding: 10px 20px; font-weight: bold;
            }
            QPushButton:hover { background: #69F0AE; }
            QPushButton:disabled { background: #555; color: #888; }
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox, QTabWidget::pane, QGroupBox {
                background-color: #1e1e2e; color: #e0e0e0;
                border: 1px solid #2d3142; border-radius: 6px;
                padding: 8px;
            }
            QTabBar::tab {
                background: #1e1e2e; color: #aaa; padding: 10px 20px;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: #4FC3F7; color: black; font-weight: bold;
            }
        """)

        from PySide6.QtWidgets import QTabWidget, QGroupBox, QFormLayout
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tabs
        self.enouse_tab = ENouseTab()
        self.sim_tab = SimulationTab()
        
        self.tabs.addTab(self.enouse_tab, "👃 E-Nouse Visualizer")
        self.tabs.addTab(self.sim_tab, "📈 Signal Simulation")

        # Workers
        self.data_worker = WebSocketWorker(WS_URL, is_log=False)
        self.data_worker.data_received.connect(self.enouse_tab.update_graph)
        self.data_worker.start()

        self.log_worker = WebSocketWorker(WS_LOG_URL, is_log=True)
        self.log_worker.log_received.connect(self.enouse_tab.update_log)
        self.log_worker.start()

        self.sim_worker = WebSocketWorker(WS_SIM_URL, is_log=False)
        self.sim_worker.data_received.connect(self.sim_tab.update_graph)
        self.sim_worker.start()

        # Initial refresh
        QTimer.singleShot(1000, self.enouse_tab.refresh_ports)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
