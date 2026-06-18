import numpy as np
from .base_feature import BaseFeature


class HipRotation(BaseFeature):
    def __init__(self, side: str, ukf=None, ema_alpha=0.1):
        super().__init__(f"{side}_hip_rotation", ema_alpha)
        self.side = side
        self.hip = f"{side}_hip"
        self.knee = f"{side}_knee"
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        hip = world_landmarks.get(self.hip)
        knee = world_landmarks.get(self.knee)
        if not hip or not knee:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }
        t = np.array([knee[0] - hip[0], knee[2] - hip[2]])
        yaw = np.arctan2(-t[1], -t[0])
        if self.ukf:
            yaw = self.ukf.update(yaw)

        raw_val = yaw
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.2
        conf = min(1.0, visibility.get(self.hip, 0) * visibility.get(self.knee, 0))
        if abs(corrected) < threshold:
            likelihood = 0.0
            rot_side = "none"
        else:
            likelihood = min(1.0, (abs(corrected) - threshold) / threshold)
            rot_side = "left" if corrected > 0 else "right"
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": rot_side,
            "confidence": conf,
            "raw_value": raw_val,
        }
