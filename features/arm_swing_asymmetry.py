import numpy as np
from collections import deque
from .base_feature import BaseFeature


class ArmSwingAsymmetry(BaseFeature):
    def __init__(self, window_size=20, ukf=None, ema_alpha=0.1):
        super().__init__("arm_swing_asymmetry", ema_alpha)
        self.left_angles = deque(maxlen=window_size)
        self.right_angles = deque(maxlen=window_size)
        self.ukf = ukf

    def _arm_elevation(self, shoulder, elbow):
        upper = np.array(
            [elbow[0] - shoulder[0], elbow[1] - shoulder[1], elbow[2] - shoulder[2]]
        )
        down = np.array([0.0, 1.0, 0.0])
        cosang = np.dot(upper, down) / (np.linalg.norm(upper) * np.linalg.norm(down))
        cosang = np.clip(cosang, -1.0, 1.0)
        return np.arccos(cosang)

    def compute(self, world_landmarks, image_landmarks, visibility):
        ls = world_landmarks.get("left_shoulder")
        le = world_landmarks.get("left_elbow")
        rs = world_landmarks.get("right_shoulder")
        re = world_landmarks.get("right_elbow")
        if not all([ls, le, rs, re]):
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }

        left_ang = self._arm_elevation(ls, le)
        right_ang = self._arm_elevation(rs, re)
        self.left_angles.append(left_ang)
        self.right_angles.append(right_ang)

        if len(self.left_angles) < 5:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }

        left_amp = max(self.left_angles) - min(self.left_angles)
        right_amp = max(self.right_angles) - min(self.right_angles)
        asymmetry = left_amp - right_amp

        if self.ukf:
            asymmetry = self.ukf.update(asymmetry)

        raw_val = asymmetry
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.15
        conf = min(
            1.0,
            visibility.get("left_shoulder", 0) * visibility.get("right_shoulder", 0),
        )
        if abs(corrected) < threshold:
            likelihood = 0.0
            side = "none"
        else:
            likelihood = min(1.0, abs(corrected) / 0.4)
            side = "left" if corrected < 0 else "right"
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": side,
            "confidence": conf,
            "raw_value": raw_val,
        }
