import numpy as np
from .base_feature import BaseFeature


class StepWidth(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("step_width_asymmetry", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        la = world_landmarks.get("left_ankle")
        ra = world_landmarks.get("right_ankle")
        if not la or not ra:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }

        width = abs(la[0] - ra[0])
        raw_val = width
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.08
        conf = min(
            1.0, visibility.get("left_ankle", 0) * visibility.get("right_ankle", 0)
        )
        if abs(corrected) < threshold:
            likelihood = 0.0
        else:
            likelihood = min(1.0, abs(corrected) / 0.25)
        likelihood *= conf

        side = "none"
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": side,
            "confidence": conf,
            "raw_value": raw_val,
        }
