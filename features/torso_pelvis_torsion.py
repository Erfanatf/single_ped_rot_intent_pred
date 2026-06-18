import numpy as np
from .base_feature import BaseFeature


class TorsoPelvisTorsion(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("torso_pelvis_torsion", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        ls = world_landmarks.get("left_shoulder")
        rs = world_landmarks.get("right_shoulder")
        lh = world_landmarks.get("left_hip")
        rh = world_landmarks.get("right_hip")
        if not all([ls, rs, lh, rh]):
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }

        s = np.array([rs[0] - ls[0], rs[2] - ls[2]])
        p = np.array([rh[0] - lh[0], rh[2] - lh[2]])
        yaw_shoulder = np.arctan2(-s[1], -s[0])
        yaw_pelvis = np.arctan2(-p[1], -p[0])
        torsion = (yaw_shoulder - yaw_pelvis + np.pi) % (2 * np.pi) - np.pi

        if self.ukf:
            torsion = self.ukf.update(torsion)

        raw_val = torsion
        corrected = self.apply_ema_bias(raw_val)  # continuously adaptive

        threshold = 0.1
        if abs(corrected) < threshold:
            likelihood = 0.0
            side = "none"
        else:
            likelihood = min(1.0, (abs(corrected) - threshold) / threshold)
            side = "left" if corrected > 0 else "right"

        conf = min(
            1.0,
            visibility.get("left_shoulder", 0)
            * visibility.get("right_shoulder", 0)
            * visibility.get("left_hip", 0)
            * visibility.get("right_hip", 0),
        )
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": side,
            "confidence": conf,
            "raw_value": raw_val,
        }
