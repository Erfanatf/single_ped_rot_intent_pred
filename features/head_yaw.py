import numpy as np
from .base_feature import BaseFeature


class HeadYaw(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("head_yaw", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        le = world_landmarks.get("left_ear")
        re = world_landmarks.get("right_ear")
        if not le or not re:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }
        e = np.array([re[0] - le[0], re[2] - le[2]])
        yaw = np.arctan2(-e[1], -e[0])
        if self.ukf:
            yaw = self.ukf.update(yaw)

        raw_val = yaw
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.18
        conf = min(1.0, visibility.get("left_ear", 0) * visibility.get("right_ear", 0))
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
