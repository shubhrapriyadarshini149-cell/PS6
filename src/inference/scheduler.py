import time
import logging

class InferenceScheduler:
    def __init__(self, cameras, models, max_fps=10.0):
        """
        cameras: list of CameraThread objects
        models: list of loaded ModelAdapter objects
        max_fps: total global inference budget (frames per second across all cameras)
        """
        self.cameras = [c for c in cameras if c.is_running]
        self.models = models
        self.max_fps = max_fps
        self.min_loop_time = 1.0 / max_fps if max_fps > 0 else 0
        self.is_running = False
        
        # We store the latest detection results per camera here
        self.latest_results = {cam.name: [] for cam in self.cameras}

    def start(self):
        self.is_running = True
        logging.info(f"Starting Inference Scheduler with {len(self.cameras)} cameras and {len(self.models)} models.")
        
        camera_idx = 0
        while self.is_running:
            loop_start = time.time()
            
            if not self.cameras:
                time.sleep(1.0)
                continue
                
            cam = self.cameras[camera_idx]
            frame, timestamp = cam.get_latest_frame()
            
            if frame is not None:
                all_detections = []
                for model in self.models:
                    # Run each model on the frame
                    try:
                        dets = model.predict(frame)
                        all_detections.extend(dets)
                    except Exception as e:
                        logging.error(f"Inference error on model {model.config_key}: {e}")
                
                self.latest_results[cam.name] = all_detections
            
            # Move to next camera (round robin)
            camera_idx = (camera_idx + 1) % len(self.cameras)
            
            # Enforce inference budget
            elapsed = time.time() - loop_start
            sleep_time = self.min_loop_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
        self.is_running = False
