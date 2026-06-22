import cv2
import numpy as np
import requests
import threading
import time
from requests.auth import HTTPBasicAuth

class MJPEGReader:
    """Reads an MJPEG HTTP stream and provides frames like a VideoCapture object."""

    def __init__(self, url, timeout=5.0, username=None, password=None):
        self.url = url
        self.timeout = timeout
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        self.thread = None
        self.error = None

    def start(self):
        """Start the background stream reader thread."""
        self.running = True
        self.thread = threading.Thread(target=self._read_stream, daemon=True)
        self.thread.start()
        waited = 0
        while self.frame is None and self.error is None and waited < 5:
            time.sleep(0.1)
            waited += 0.1

    def _read_stream(self):
        try:
            resp = requests.get(self.url, stream=True, timeout=self.timeout, auth=self.auth)
            if resp.status_code != 200:
                self.error = f"HTTP {resp.status_code}"
                self.running = False
                return

            byte_buffer = b""
            for chunk in resp.iter_content(chunk_size=1024):
                if not self.running:
                    break
                byte_buffer += chunk
                start = byte_buffer.find(b"\xff\xd8")
                end = byte_buffer.find(b"\xff\xd9")
                while start != -1 and end != -1 and start < end:
                    jpeg_data = byte_buffer[start : end + 2]
                    byte_buffer = byte_buffer[end + 2 :]
                    try:
                        arr = np.frombuffer(jpeg_data, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            with self.lock:
                                self.frame = frame
                    except Exception:
                        pass
                    start = byte_buffer.find(b"\xff\xd8")
                    end = byte_buffer.find(b"\xff\xd9")
        except Exception as e:
            self.error = str(e)
        finally:
            self.running = False

    def read(self):
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
        if self.error:
            print(f"MJPEGReader error: {self.error}")
            self.error = None
        return False, None

    def isOpened(self):
        return self.running or self.frame is not None

    def release(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)