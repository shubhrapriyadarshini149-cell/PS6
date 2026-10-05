# Common Commands

This file contains the essential commands to run and test the Factory Safety Monitor project. All commands assume you are running them from the root of the project directory (`e:\PS6`).

## 1. Start the Live Dashboard Server
The core application is run through the FastAPI server. It hosts the API, the inference engine, and the web UI.

**Command:**
```powershell
.\venv\Scripts\python.exe src\server\app.py
```

*Once running, open a web browser and go to: `http://localhost:8000`*

## 2. Testing the Ingest Layer
If you want to debug camera connectivity or dropping frames without running the full dashboard.

**Command:**
```powershell
.\venv\Scripts\python.exe tests\test_ingest.py
```

## 3. Testing the Full Pipeline (Golden Clip)
If you want to run the model against the sample video and verify that alerts are being generated in the `alerts.db` SQLite database and snapshots are saved, without a web UI.

**Command:**
```powershell
.\venv\Scripts\python.exe tests\test_golden_clip.py
```

## 4. Install Dependencies
If you ever pull new code or need to reinstall the environment.

**Command:**
```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\pip.exe install fastapi uvicorn websockets
```
