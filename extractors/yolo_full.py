import cv2
import numpy as np
from ultralytics import YOLO
from .base import BasePoseExtractor

COCO_KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

class YOLOFullExtractor(BasePoseExtractor):
    def __init__(self, config: dict):
        yolo_cfg = config.get('yolo', {})
        model_path = yolo_cfg.get('model_path', 'yolov8n-pose.pt')
        self.model = YOLO(model_path)

    def extract(self, frame) -> tuple:
        results = self.model(frame, verbose=False)
        image_lm = {}
        world_lm = {}      # YOLO has no 3D landmarks
        visibility = {}

        if results and len(results[0].keypoints) > 0:
            kp = results[0].keypoints.xy[0].cpu().numpy()        # (17,2)
            confs = results[0].keypoints.conf[0].cpu().numpy() if hasattr(results[0].keypoints, 'conf') else np.ones(17)
            for i, name in enumerate(COCO_KEYPOINT_NAMES):
                if i < len(kp):
                    x, y = kp[i]
                    if x != 0 or y != 0:
                        image_lm[name] = [float(x), float(y)]
                        visibility[name] = float(confs[i])
        return image_lm, world_lm, visibility