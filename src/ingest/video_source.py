import cv2
import time
import logging
import os
from .mjpeg_reader import MJPEGReader

class VideoSource:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.type = config.get("type", "rtsp")
        self.url = config.get("url")
        self.cap = None
        self.mjpeg_reader = None
        
    def connect(self):
        if self.type == "mjpeg":
            username = self.config.get("username")
            password = self.config.get("password")
            verify_tls = self.config.get("verify_tls", False)
            self.mjpeg_reader = MJPEGReader(self.url, username, password, verify_tls)
            return self.mjpeg_reader.connect()
        elif self.type == "h264" or self.type == "rtsp" or self.type == "webcam":
            # For webcam, URL is usually an int
            source = int(self.url) if str(self.url).isdigit() else self.url
            # Set TCP transport for RTSP to reduce artifacts (Android check 6)
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp" if "rtsp://" in str(self.url) else ""
            self.cap = cv2.VideoCapture(source)
            return self.cap.isOpened()
        elif self.type == "file_loop":
            self.cap = cv2.VideoCapture(self.url)
            return self.cap.isOpened()
        return False
        
    def read(self):
        if self.type == "mjpeg" and self.mjpeg_reader:
            return self.mjpeg_reader.read_frame()
        elif self.cap:
            ret, frame = self.cap.read()
            if not ret and self.type == "file_loop":
                # Restart video for file loop
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            return ret, frame
        return False, None
        
    def release(self):
        if self.cap:
            self.cap.release()
        if self.mjpeg_reader:
            self.mjpeg_reader.stream = None
