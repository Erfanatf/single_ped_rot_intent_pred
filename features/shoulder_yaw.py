import numpy as np
from .base_feature import BaseFeature


class ShoulderYaw(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("shoulder_yaw", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        ls = world_landmarks.get("left_shoulder")
        rs = world_landmarks.get("right_shoulder")
        if not ls or not rs:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }
        s = np.array([rs[0] - ls[0], rs[2] - ls[2]])
        yaw = np.arctan2(-s[1], -s[0])
        if self.ukf:
            yaw = self.ukf.update(yaw)

        raw_val = yaw
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.10
        conf = min(
            1.0,
            visibility.get("left_shoulder", 0) * visibility.get("right_shoulder", 0),
        )
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
