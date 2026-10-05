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
    webcam_cam = CameraThread("Laptop_Webcam", webcam_config)
    webcam_cam.start()
    camera_threads["Laptop_Webcam"] = webcam_cam
    
    global_scheduler = InferenceScheduler(cameras=[webcam_cam], models=[ppe_adapter], max_fps=10.0)
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

@app.post("/api/cameras")
async def add_camera(req: CameraRequest):
    global global_scheduler
    
    config = {
        "type": req.type,
        "url": req.url,
        "username": req.username,
        "password": req.password,
        "verify_tls": req.verify_tls
    }
    
    # Stop existing if any
    if req.name in camera_threads:
        camera_threads[req.name].stop()
        
    cam = CameraThread(req.name, config)
    cam.start()
    
    camera_threads[req.name] = cam
    global_scheduler.cameras.append(cam)
    
    return {"status": "success", "message": f"Camera {req.name} added."}

@app.get("/api/cameras")
async def get_cameras():
    cameras = []
    for name, cam in camera_threads.items():
        cameras.append(cam.get_health_stats())
    return {"cameras": cameras}

@app.get("/api/alerts")
async def get_alerts():
    # Placeholder for fetching alerts from SQLite DB
    return {"alerts": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server.app:app", host="0.0.0.0", port=8000, reload=False)
