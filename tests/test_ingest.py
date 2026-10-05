import time
import logging
import cv2
import sys
import os

# Add src to python path for testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.ingest.camera_thread import CameraThread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_ingest_layer():
    # We will test using a public test RTSP stream, or a local webcam (0)
    config = {
        "type": "webcam",
        "url": 0 # Change to an RTSP link to test drops
    }
    
    print("Initializing camera thread (Simulating slow consumer)...")
    cam = CameraThread("test_cam", config)
    cam.start()
    
    print("Sleeping for 5 seconds to let the buffer run...")
    time.sleep(5)
    
    stats = cam.get_health_stats()
    print(f"Health Stats: {stats}")
    
    print("Reading frames very slowly (simulating slow inference bottleneck)...")
    for _ in range(5):
        frame, timestamp = cam.get_latest_frame()
        if frame is not None:
            print(f"Got frame from timestamp {timestamp}, shape: {frame.shape}")
        else:
            print("No frame yet.")
        time.sleep(1.0) # Slow consumer
        
    stats = cam.get_health_stats()
    print(f"Health Stats after slow consumption: {stats}")
    
    cam.stop()
    cam.join(timeout=2)
    print("Test finished.")

if __name__ == "__main__":
    test_ingest_layer()
