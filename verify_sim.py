import requests
import time
import websocket
import json
import threading

API_URL = "http://localhost:3000"
WS_SIM_URL = "ws://localhost:3000/sim/ws"

def test_api():
    print("Testing API...")
    
    # Start Sim
    res = requests.post(f"{API_URL}/sim/start")
    print(f"Start Sim: {res.status_code} - {res.json()}")
    assert res.status_code == 200
    
    # Update Params
    payload = {
        "signal1": {"amplitude": 5.0, "frequency": 2.0, "phase": 0.0},
        "signal2": {"amplitude": 2.0, "frequency": 5.0, "phase": 90.0},
        "operation": "Add"
    }
    res = requests.post(f"{API_URL}/sim/params", json=payload)
    print(f"Update Params: {res.status_code} - {res.json()}")
    assert res.status_code == 200

    # Wait a bit
    time.sleep(1)

    # Stop Sim
    res = requests.post(f"{API_URL}/sim/stop")
    print(f"Stop Sim: {res.status_code} - {res.json()}")
    assert res.status_code == 200

def on_message(ws, message):
    data = json.loads(message)
    print(f"WS Recv: {data}")
    ws.close()

def test_ws():
    print("Testing WebSocket...")
    # Start sim first
    requests.post(f"{API_URL}/sim/start")
    
    ws = websocket.WebSocketApp(WS_SIM_URL, on_message=on_message)
    ws.run_forever()
    
    requests.post(f"{API_URL}/sim/stop")

if __name__ == "__main__":
    try:
        test_api()
        test_ws()
        print("[SUCCESS] Verification Successful!")
    except Exception as e:
        print(f"[FAILED] Verification Failed: {e}")
