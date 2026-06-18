import cv2
import time
import mediapipe as mp
from .base import BasePoseExtractor

MP_KEYPOINT_NAMES = {
    0: "nose",
    1: "left_eye_inner", 2: "left_eye", 3: "left_eye_outer",
    4: "right_eye_inner", 5: "right_eye", 6: "right_eye_outer",
    7: "left_ear", 8: "right_ear",
    9: "mouth_left", 10: "mouth_right",
    11: "left_shoulder", 12: "right_shoulder",
    13: "left_elbow", 14: "right_elbow",
    15: "left_wrist", 16: "right_wrist",
    17: "left_pinky", 18: "right_pinky",
    19: "left_index", 20: "right_index",
    21: "left_thumb", 22: "right_thumb",
    23: "left_hip", 24: "right_hip",
    25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle",
    29: "left_heel", 30: "right_heel",
    31: "left_foot_index", 32: "right_foot_index"
}

class MediaPipeFullExtractor(BasePoseExtractor):
    def __init__(self, config: dict):
        mp_cfg = config.get('mediapipe', {})
        model_path = mp_cfg.get('model_path', 'pose_landmarker_lite.task')
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.VIDEO
        )
        self.detector = PoseLandmarker.create_from_options(options)

    def extract(self, frame) -> tuple:
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.time() * 1000)
        result = self.detector.detect_for_video(mp_image, timestamp_ms)

        image_lm = {}
        world_lm = {}
        visibility = {}

        if result.pose_landmarks and result.pose_world_landmarks:
            img_landmarks = result.pose_landmarks[0]
            world_landmarks = result.pose_world_landmarks[0]
            for idx, name in MP_KEYPOINT_NAMES.items():
                img = img_landmarks[idx]
                world = world_landmarks[idx]
                # Pixel coordinates in the original frame size (will be scaled later)
                image_lm[name] = [img.x * w, img.y * h]
                # World coordinates (body‑centric, in metres)
                world_lm[name] = [world.x, world.y, world.z]
                visibility[name] = img.visibility

        return image_lm, world_lm, visibility