import numpy as np
from .base_feature import BaseFeature


class PelvisYaw(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("pelvis_yaw", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        lh = world_landmarks.get("left_hip")
        rh = world_landmarks.get("right_hip")
        if not lh or not rh:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }
        p = np.array([rh[0] - lh[0], rh[2] - lh[2]])
        yaw = np.arctan2(-p[1], -p[0])
        if self.ukf:
            yaw = self.ukf.update(yaw)

        raw_val = yaw
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.15
        conf = min(1.0, visibility.get("left_hip", 0) * visibility.get("right_hip", 0))
        if abs(corrected) < threshold:
            likelihood = 0.0
            side = "none"
        else:
            likelihood = min(1.0, (abs(corrected) - threshold) / threshold)
            side = "left" if corrected > 0 else "right"
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": side,
            "confidence": conf,
            "raw_value": raw_val,
        }
