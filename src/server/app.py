import cv2
import threading
import time
import os
import yaml
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.ingest.camera_thread import CameraThread
from src.inference.adapter import ModelAdapter
from src.inference.scheduler import InferenceScheduler
from src.server.draw import draw_annotations

app = FastAPI(title="Factory Safety Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

os.makedirs("src/server/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="src/server/static"), name="static")

global_scheduler = None
camera_threads = {}

@app.on_event("startup")
def startup_event():
    global global_scheduler
    
    # Load model config
    with open("config/models.yaml", "r") as f:
        models_config = yaml.safe_load(f)["models"]
        
    ppe_config = models_config.get("ppe_primary")
    ppe_adapter = ModelAdapter("ppe_primary", ppe_config)
    ppe_adapter.load()
    
    # Auto-attach local webcam
    webcam_config = {
        "type": "webcam",
        "url": 0,
        "username": "",
        "password": "",
        "verify_tls": False
    }
    webcam_cam = CameraThread("Laptop Webcam", webcam_config)
    webcam_cam.start()
    camera_threads["Laptop Webcam"] = webcam_cam
    
    from src.alerts.engine import AlertEngine
    from src.rules.zone_rules import ZoneRules
    os.makedirs("src/server/static/snapshots", exist_ok=True)
    alert_engine = AlertEngine(db_path="alerts.db", snapshot_dir="src/server/static/snapshots", cooldown_seconds=60)
    zone_rules = ZoneRules("config/rules.yaml")
    
    global_scheduler = InferenceScheduler(
        cameras=[webcam_cam], 
        models=[ppe_adapter], 
        max_fps=20.0,
        alert_engine=alert_engine,
        zone_rules=zone_rules
    )
    threading.Thread(target=global_scheduler.start, daemon=True).start()

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("src/server/static/index.html")

def generate_mjpeg_stream(camera_name: str):
    """Yields annotated JPEG frames for a specific camera."""
    while True:
        if camera_name not in camera_threads:
            time.sleep(1.0)
            continue
            
        cam = camera_threads[camera_name]
        frame, _ = cam.get_latest_frame()
        
        if frame is not None:
            # Get latest inference results
            detections = global_scheduler.latest_results.get(camera_name, [])
            annotated = draw_annotations(frame, detections)
            
            ret, buffer = cv2.imencode('.jpg', annotated)
            if ret:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
        time.sleep(0.05) # ~20 FPS limit for streaming

@app.get("/stream/{camera_name}")
async def video_feed(camera_name: str):
    return StreamingResponse(
        generate_mjpeg_stream(camera_name), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

class CameraRequest(BaseModel):
    name: str
    type: str # 'webcam', 'mjpeg', 'h264', 'file_loop'
    url: str
    username: str = ""
    password: str = ""
    verify_tls: bool = False
    original_name: str = ""

@app.post("/api/cameras")
async def add_or_update_camera(req: CameraRequest):
    global global_scheduler
    
    target_name = req.original_name if req.original_name else req.name
    
    # If replacing or editing existing camera
    if target_name in camera_threads:
        old_cam = camera_threads.pop(target_name)
        old_cam.stop()
        if global_scheduler:
            global_scheduler.cameras = [c for c in global_scheduler.cameras if c.name != target_name]
            if target_name in global_scheduler.latest_results:
                del global_scheduler.latest_results[target_name]

    # If renamed to a name that already exists, stop that too
    if req.name in camera_threads:
        old_cam = camera_threads.pop(req.name)
        old_cam.stop()
        if global_scheduler:
            global_scheduler.cameras = [c for c in global_scheduler.cameras if c.name != req.name]

    config = {
        "type": req.type,
        "url": req.url,
        "username": req.username,
        "password": req.password,
        "verify_tls": req.verify_tls
    }
    
    cam = CameraThread(req.name, config)
    cam.start()
    
    camera_threads[req.name] = cam
    if global_scheduler:
        global_scheduler.cameras.append(cam)
    
    return {"status": "success", "message": f"Camera {req.name} configured successfully."}

@app.put("/api/cameras/{camera_name}")
async def update_camera(camera_name: str, req: CameraRequest):
    req.original_name = camera_name
    return await add_or_update_camera(req)

@app.delete("/api/cameras/{camera_name}")
async def delete_camera(camera_name: str):
    global global_scheduler
    if camera_name in camera_threads:
        cam = camera_threads.pop(camera_name)
        cam.stop()
        if global_scheduler:
            global_scheduler.cameras = [c for c in global_scheduler.cameras if c.name != camera_name]
            if camera_name in global_scheduler.latest_results:
                del global_scheduler.latest_results[camera_name]
        return {"status": "success", "message": f"Camera {camera_name} removed."}
    return {"status": "error", "message": f"Camera {camera_name} not found."}

@app.get("/api/cameras")
async def get_cameras():
    cameras = []
    for name, cam in camera_threads.items():
        cameras.append(cam.get_health_stats())
    return {"cameras": cameras}

@app.get("/api/alerts")
async def get_alerts():
    if global_scheduler and global_scheduler.alert_engine:
        return {"alerts": global_scheduler.alert_engine.get_recent_alerts(limit=30)}
    return {"alerts": []}

@app.get("/api/summary")
async def get_summary():
    import sqlite3
    total_alerts = 0
    by_type = {}
    by_camera = {}
    recent_1h = 0
    try:
        conn = sqlite3.connect("alerts.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM alerts")
        total_alerts = c.fetchone()[0]
        
        c.execute("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
        by_type = dict(c.fetchall())
        
        c.execute("SELECT camera, COUNT(*) FROM alerts GROUP BY camera")
        by_camera = dict(c.fetchall())
        
        c.execute("SELECT COUNT(*) FROM alerts WHERE timestamp >= datetime('now', '-1 hour')")
        recent_1h = c.fetchone()[0]
        conn.close()
    except Exception as e:
        pass
    
    # Compute active worker count and compliance from active scheduler results
    total_tracked = 0
    total_compliant = 0
    active_violations = 0
    
    if global_scheduler:
        for cam_name, detections in global_scheduler.latest_results.items():
            for d in detections:
                cls = d.get("class", "")
                if cls in ["person", "no-hardhat", "no-vest"]:
                    total_tracked += 1
                    equipment = d.get("equipment", [])
                    if cls in ["no-hardhat", "no-vest"] or "no-hardhat" in equipment or "no-vest" in equipment:
                        active_violations += 1
                    else:
                        total_compliant += 1
                        
    compliance_rate = round((total_compliant / max(1, total_tracked)) * 100) if total_tracked > 0 else 100
    active_streams = len([c for c in camera_threads.values() if c.is_running])
    has_fire = by_type.get("fire", 0) > 0 or by_type.get("smoke", 0) > 0

    recent_alerts = []
    if global_scheduler and global_scheduler.alert_engine:
        recent_alerts = global_scheduler.alert_engine.get_recent_alerts(limit=15)
    
    return {
        "total_alerts": total_alerts,
        "recent_1h": recent_1h,
        "active_streams": active_streams,
        "workers_tracked": total_tracked,
        "workers_compliant": total_compliant,
        "active_violations": active_violations,
        "compliance_rate": compliance_rate,
        "by_type": by_type,
        "by_camera": by_camera,
        "hazard_status": "Hazard Alert 🔴" if has_fire else "Normal 🟢",
        "recent_alerts": recent_alerts
    }

@app.post("/api/alerts/clear")
async def clear_alerts():
    import sqlite3
    conn = sqlite3.connect("alerts.db")
    c = conn.cursor()
    c.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()
    if global_scheduler and global_scheduler.alert_engine:
        global_scheduler.alert_engine.cooldowns.clear()
        global_scheduler.alert_engine.recent_alerts.clear()
    return {"status": "success", "message": "Alert logs cleared."}

@app.get("/api/sources/available")
async def get_sources_available():
    import socket
    videos = []
    clips_dir = "eval/data/clips"
    if os.path.exists(clips_dir):
        for f in sorted(os.listdir(clips_dir)):
            if f.lower().endswith((".mp4", ".avi", ".mkv", ".mov")):
                full_path = os.path.join(clips_dir, f).replace("\\", "/")
                try:
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 1)
                except Exception:
                    size_mb = 0.0
                
                label = f.rsplit(".", 1)[0].replace("_", " ").title().strip()
                videos.append({
                    "name": label,
                    "filename": f,
                    "path": full_path,
                    "size_mb": size_mb,
                    "type": "file_loop"
                })
                
    cameras = []
    
    # 1. Local Webcam
    cameras.append({
        "name": "Laptop Webcam",
        "type": "webcam",
        "url": "0",
        "reachable": True,
        "description": "Device 0 (Integrated)"
    })
    
    # 2. Check Android IP camera reachability
    def check_port(ip, port, timeout=0.2):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            r = s.connect_ex((ip, port))
            s.close()
            return r == 0
        except Exception:
            return False

    candidate_ips = ["10.79.84.100", "192.168.43.1"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        prefix = ".".join(local_ip.split(".")[:-1])
        candidate_ips.extend([f"{prefix}.1", f"{prefix}.100"])
    except Exception:
        pass

    seen_ips = set()
    unique_candidates = []
    for ip in candidate_ips:
        if ip not in seen_ips:
            seen_ips.add(ip)
            unique_candidates.append(ip)

    found_phone = False
    for ip in unique_candidates:
        if check_port(ip, 4444):
            cameras.append({
                "name": "Android Phone",
                "type": "mjpeg",
                "url": f"https://{ip}:4444/video/mjpeg",
                "username": "",
                "password": "",
                "verify_tls": False,
                "reachable": True,
                "description": f"{ip}:4444 • Active"
            })
            found_phone = True
            break
        elif check_port(ip, 8080):
            cameras.append({
                "name": "Android Phone",
                "type": "mjpeg",
                "url": f"http://{ip}:8080/video/mjpeg",
                "username": "",
                "password": "",
                "verify_tls": False,
                "reachable": True,
                "description": f"{ip}:8080 • Active"
            })
            found_phone = True
            break

    if not found_phone:
        cameras.append({
            "name": "Android Phone",
            "type": "mjpeg",
            "url": "https://10.79.84.100:4444/video/mjpeg",
            "username": "",
            "password": "",
            "verify_tls": False,
            "reachable": False,
            "description": "10.79.84.100:4444 (Standby)"
        })

    return {"videos": videos, "cameras": cameras}
    
@app.get("/api/system")
async def get_system_status():
    import torch
    import platform
    cuda_available = torch.cuda.is_available()
    device = "cuda:0" if cuda_available else "cpu"
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU (Software)"
    
    hardware_gpu = None
    try:
        import subprocess
        cmd = 'powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like \'*NVIDIA*\' }).Name"'
        res = subprocess.check_output(cmd, shell=True, text=True).strip()
        if res:
            hardware_gpu = res.splitlines()[0].strip()
    except Exception:
        pass
        
    return {
        "cuda_available": cuda_available,
        "device": device,
        "device_name": device_name,
        "hardware_gpu": hardware_gpu or device_name,
        "python": platform.python_version(),
        "system": f"{platform.system()} {platform.release()}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server.app:app", host="0.0.0.0", port=8000, reload=False)
