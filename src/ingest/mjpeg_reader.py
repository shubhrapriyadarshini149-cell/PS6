import cv2
import numpy as np
import requests
import urllib3
import logging

# Suppress insecure request warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MJPEGReader:
    def __init__(self, url, username=None, password=None, verify_tls=False):
        self.url = url
        self.auth = (username, password) if username and password else None
        self.verify_tls = verify_tls
        self.stream = None
        self.bytes_buffer = bytes()

    def connect(self):
        try:
            self.stream = requests.get(
                self.url,
                auth=self.auth,
                verify=self.verify_tls,
                stream=True,
                timeout=10
            )
            self.stream.raise_for_status()
            logging.info(f"Connected to MJPEG stream: {self.url}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to {self.url}: {e}")
            return False

    def read_frame(self):
        if not self.stream:
            return False, None

        try:
            for chunk in self.stream.iter_content(chunk_size=1024):
                self.bytes_buffer += chunk
                a = self.bytes_buffer.find(b'\xff\xd8') # JPEG start
                b = self.bytes_buffer.find(b'\xff\xd9') # JPEG end
                if a != -1 and b != -1:
                    jpg = self.bytes_buffer[a:b+2]
                    self.bytes_buffer = self.bytes_buffer[b+2:]
                    img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    return True, img
        except Exception as e:
            logging.error(f"Error reading frame: {e}")
            self.stream = None
            
        return False, None
