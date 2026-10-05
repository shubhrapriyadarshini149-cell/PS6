import threading
import time
import logging
from .video_source import VideoSource

class CameraThread(threading.Thread):
    def __init__(self, name, config):
        super().__init__(daemon=True)
        self.name = name
        self.config = config
        self.source = VideoSource(name, config)
        
        # Latest frame buffer logic
        self.lock = threading.Lock()
        self.latest_frame = None
        self.last_frame_time = 0
        
        # Health stats
        self.fps = 0.0
        self.reconnect_count = 0
        self.is_running = True
        
        # Control flags
        self._frame_count = 0
        self._fps_start_time = time.time()

    def run(self):
        logging.info(f"Starting thread for camera {self.name}")
        while self.is_running:
            if not self.source.connect():
                self.reconnect_count += 1
                logging.warning(f"[{self.name}] Failed to connect. Retrying in {min(2 ** self.reconnect_count, 30)}s...")
                time.sleep(min(2 ** self.reconnect_count, 30))
                continue
            
            self.reconnect_count = 0
            logging.info(f"[{self.name}] Connected.")
            
            while self.is_running:
                loop_start = time.time()
                ret, frame = self.source.read()
                if not ret:
                    logging.warning(f"[{self.name}] Stream dropped. Reconnecting...")
                    break
                    
                now = time.time()
                with self.lock:
                    self.latest_frame = frame
                    self.last_frame_time = now
                    
                self._update_fps(now)

                # Pace video files to their real-world native FPS (e.g. 25-30 FPS)
                if self.source.type == "file_loop":
                    target_interval = 1.0 / self.source.fps if self.source.fps > 0 else 0.033
                    elapsed = time.time() - loop_start
                    sleep_time = target_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
            self.source.release()
            
    def _update_fps(self, now):
        self._frame_count += 1
        elapsed = now - self._fps_start_time
        if elapsed > 2.0:
            self.fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_start_time = now

    def get_latest_frame(self):
        with self.lock:
            return self.latest_frame, self.last_frame_time

    def get_health_stats(self):
        now = time.time()
        age = now - self.last_frame_time if self.last_frame_time > 0 else -1
        return {
            "name": self.name,
            "type": self.config.get("type", "webcam"),
            "url": str(self.config.get("url", "")),
            "username": self.config.get("username", ""),
            "verify_tls": bool(self.config.get("verify_tls", False)),
            "fps": round(self.fps, 1),
            "last_frame_age": round(age, 2),
            "reconnect_count": self.reconnect_count,
            "is_alive": age >= 0 and age < 5.0
        }
        
    def stop(self):
        self.is_running = False
        self.source.release()
