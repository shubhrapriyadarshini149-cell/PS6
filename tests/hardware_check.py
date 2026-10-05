import platform
import psutil
try:
    import torch
    has_torch = True
except ImportError:
    has_torch = False
import time
import os

def print_hardware_info():
    print("=== Hardware Check ===")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Processor: {platform.processor()}")
    
    # RAM
    ram = psutil.virtual_memory()
    print(f"Total RAM: {ram.total / (1024**3):.2f} GB")
    print(f"Available RAM: {ram.available / (1024**3):.2f} GB")
    
    # CPU usage
    print(f"CPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical")
    
    # GPU
    if has_torch:
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"CUDA Version: {torch.version.cuda}")
        else:
            print("GPU: None (CUDA not available in PyTorch)")
    else:
        print("GPU: PyTorch not installed to check")
    print("======================")

def check_inference_speed():
    print("\n=== YOLOv8 Inference Speed Check ===")
    try:
        from ultralytics import YOLO
        import cv2
        import numpy as np
    except ImportError:
        print("Ultralytics or OpenCV not installed.")
        return
        
    print("Loading YOLOv8n (nano)...")
    model_n = YOLO("yolov8n.pt") # Will download if missing
    
    print("Loading YOLOv8m (medium)...")
    model_m = YOLO("yolov8m.pt")
    
    # Create dummy image
    img = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    print("Warming up models...")
    _ = model_n(img, verbose=False)
    _ = model_m(img, verbose=False)
    
    n_iters = 20
    
    t0 = time.time()
    for _ in range(n_iters):
        _ = model_n(img, verbose=False)
    t1 = time.time()
    fps_n = n_iters / (t1 - t0)
    
    t0 = time.time()
    for _ in range(n_iters):
        _ = model_m(img, verbose=False)
    t1 = time.time()
    fps_m = n_iters / (t1 - t0)
    
    print(f"YOLOv8n (nano) FPS: {fps_n:.2f}")
    print(f"YOLOv8m (medium) FPS: {fps_m:.2f}")
    print("====================================")

if __name__ == "__main__":
    print_hardware_info()
    check_inference_speed()
