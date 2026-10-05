# Common Commands Reference Guide

This guide documents all essential setup, download, execution, testing, and debugging commands for the **AI Factory Safety Monitoring System (PS06)**.

All commands should be executed from the project root directory in PowerShell:
```powershell
d:\Project\PS6
```

---

## 1. Environment Setup

### Create Python Virtual Environment
Use the installed Python to create an isolated virtual environment (`venv`):
```powershell
python -m venv venv
```

### Activate Virtual Environment (Optional)
To activate in your PowerShell session:
```powershell
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or directly call `.\venv\Scripts\python.exe` and `.\venv\Scripts\pip.exe`)*

---

## 2. Dependency Installation

### Install Core Application Requirements
Installs PyTorch, OpenCV, Ultralytics, FastAPI, Uvicorn, Lapx (ByteTrack), PyYAML, SQLAlchemy, etc.:
```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

### Install Weight Download Utility
`huggingface_hub` is required to automatically fetch model weights from Hugging Face:
```powershell
.\venv\Scripts\pip.exe install huggingface_hub
```

---

## 3. Data & Model Weights Acquisition

### Download Sample Test Videos
Downloads sample MP4 video clips (`sample_workers.mp4` and `sample_people.mp4`) into `eval/data/clips/`:
```powershell
.\venv\Scripts\python.exe tests\download_sample_videos.py
```
To ensure the `virtual_clip_1` camera loop config works without manual intervention:
```powershell
Copy-Item eval\data\clips\sample_workers.mp4 eval\data\clips\sample_clip.mp4
```

### Download Pre-trained YOLOv8 Weights
Downloads primary and challenger PPE models plus the fire/smoke detection model into `models/`:
- `models/ppe_primary.pt` (`Hexmon/vyra-yolo-ppe-detection`)
- `models/ppe_challenger.pt` (`ayushgupta7777/safetyvision-yolov8`)
- `models/fire_primary.pt` (`rabahdev/fire-smoke-yolov8n`)

```powershell
.\venv\Scripts\python.exe tests\download_weights.py
```

---

## 4. Running the Live Dashboard Server

### Start the Server
Launches the FastAPI server hosting the REST API, MJPEG video feeds, inference engine, and web dashboard:
```powershell
.\venv\Scripts\python.exe src\server\app.py
```

- **Dashboard UI**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Active Cameras API**: [http://localhost:8000/api/cameras](http://localhost:8000/api/cameras)
- **Live Stream Endpoint**: [http://localhost:8000/stream/Laptop_Webcam](http://localhost:8000/stream/Laptop_Webcam)

---

## 5. Testing & Verification

### Test Golden Clip Pipeline (End-to-End Headless Test)
Runs inference and PPE compliance checking on `eval/data/clips/sample_workers.mp4`, writes alerts to `eval/test_alerts.db`, and outputs violation snapshots:
```powershell
.\venv\Scripts\python.exe tests\test_golden_clip.py
```

### Test Video Ingest & Buffering
Simulates a slow consumer to test dropping stale frames, FPS calculation, and reconnection behavior:
```powershell
.\venv\Scripts\python.exe tests\test_ingest.py
```

### Benchmark Hardware & Inference Throughput
Reports system CPU, RAM, and GPU/CUDA availability, then benchmarks YOLOv8 nano and medium model FPS:
```powershell
.\venv\Scripts\python.exe tests\hardware_check.py
```

### Test IP Camera / Phone RTSP/MJPEG Connectivity
Tests TCP port connectivity and HTTP/HTTPS video stream endpoints for IP cameras:
```powershell
.\venv\Scripts\python.exe tests\test_ip_camera.py
```

---

## 6. Process & Health Verification

### Check If Server Port (8000) Is Listening
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

### Query Camera Health via PowerShell
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/cameras"
```

### Stop Running Server
If the server is running in the foreground, press `Ctrl + C`.  
To terminate background Python server processes:
```powershell
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*src\server\app.py*" } | Stop-Process -Force
```
