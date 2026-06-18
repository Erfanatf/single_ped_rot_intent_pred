import cv2
import numpy as np
import time
import os
import atexit
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt

class ScreenRecorder:
    def __init__(self, output_dir, fps=30):
        self.output_dir = output_dir
        self.fps = fps
        self.recording = False
        self.writer = None
        self.size = None
        self.window = None
        atexit.register(self._emergency_stop)

    def start(self, window):
        self.window = window
        # Use logical size (the size we want for the video)
        self.size = (window.width(), window.height())
        os.makedirs(self.output_dir, exist_ok=True)

        # Try codecs
        codecs = [
            (cv2.VideoWriter_fourcc(*'mp4v'), '.mp4'),
            (cv2.VideoWriter_fourcc(*'avc1'), '.mp4'),
            (cv2.VideoWriter_fourcc(*'X264'), '.mp4'),
            (cv2.VideoWriter_fourcc(*'XVID'), '.avi'),
            (cv2.VideoWriter_fourcc(*'MJPG'), '.avi'),
        ]
        for fourcc, ext in codecs:
            filename = os.path.join(self.output_dir, f"dashboard_{time.strftime('%Y%m%d_%H%M%S')}{ext}")
            self.writer = cv2.VideoWriter(filename, fourcc, self.fps, self.size)
            if self.writer.isOpened():
                self.filename = filename
                self.recording = True
                print(f"Recording started: {filename}")
                return
        raise RuntimeError("No video codec available")

    def record_frame(self):
        if not self.recording or self.window is None or not self.writer.isOpened():
            return
        try:
            # Grab the window (may be high DPI)
            pixmap = self.window.grab()
            # Scale to the exact logical size we need
            pixmap = pixmap.scaled(self.size[0], self.size[1],
                                   Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            # Convert to RGB888 (3 bytes per pixel)
            qimg = pixmap.toImage().convertToFormat(QImage.Format_RGB888)
            w, h = qimg.width(), qimg.height()
            # Create numpy array directly from the QImage bits (no copy)
            ptr = qimg.bits()
            arr = np.ndarray(
                shape=(h, w, 3),
                dtype=np.uint8,
                buffer=ptr,
                strides=(w * 3, 3, 1)
            )
            # Convert RGB → BGR for OpenCV
            frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            self.writer.write(frame)
        except Exception as e:
            print(f"Recorder frame error: {e}")

    def stop(self):
        if self.recording:
            self.recording = False
            if self.writer:
                self.writer.release()
            print("Recording stopped and saved.")

    def _emergency_stop(self):
        if self.recording:
            self.stop()