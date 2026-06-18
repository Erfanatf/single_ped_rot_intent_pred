import threading
import time
import cv2

class ThreadedDetector:
    def __init__(self, extractor, inference_size, display_downscale=1.0):
        self.extractor = extractor
        self.inference_width, self.inference_height = inference_size
        self.display_downscale = display_downscale

        self.lock = threading.Lock()
        # Store the latest raw data from inference (in inference resolution)
        self.latest_image_lm = {}
        self.latest_world_lm = {}
        self.latest_visibility = {}
        self.running = False
        self.thread = None
        self._current_frame = None   # full‑size frame from main thread

        # Scaling factors for image landmarks
        self.scale_x = 1.0
        self.scale_y = 1.0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def set_display_size(self, width, height):
        """Call from main thread when display size is known/changed."""
        self.scale_x = width / self.inference_width
        self.scale_y = height / self.inference_height

    def update_frame(self, frame):
        """Give a new full‑size frame to the background thread."""
        self._current_frame = frame

    def get_latest_data(self):
        """
        Returns (display_frame, scaled_image_landmarks, world_landmarks, visibility).
        The display_frame is the latest full‑size frame (unchanged).
        image_landmarks are scaled to the display size.
        """
        with self.lock:
            # We need a frame to return; the main loop has the latest display frame,
            # so we can just return the scaled image landmarks + raw world/vis.
            # Actually the dashboard expects the frame separately.
            # We'll return None for frame here; main loop already has it.
            return (None, self._scale_image_lm(self.latest_image_lm),
                    self.latest_world_lm.copy(), self.latest_visibility.copy())

    def _scale_image_lm(self, image_lm):
        scaled = {}
        for name, coords in image_lm.items():
            scaled[name] = [coords[0] * self.scale_x, coords[1] * self.scale_y]
        return scaled

    def _run(self):
        while self.running:
            frame = self._current_frame
            if frame is None:
                time.sleep(0.001)
                continue

            # Resize frame to inference size
            inf_frame = cv2.resize(frame, (self.inference_width, self.inference_height))
            # Run extraction
            img_lm, world_lm, vis = self.extractor.extract(inf_frame)

            with self.lock:
                self.latest_image_lm = img_lm
                self.latest_world_lm = world_lm
                self.latest_visibility = vis

            time.sleep(0.001)