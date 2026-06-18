import numpy as np
from collections import deque
from .base_feature import BaseFeature


class SwingFootOrientation(BaseFeature):
    def __init__(self, side: str, ukf=None, ema_alpha=0.1):
        super().__init__(f"{side}_swing_foot_orientation", ema_alpha, is_circular=True)
        self.side = side
        self.heel = f"{side}_heel"
        self.foot_index = f"{side}_foot_index"
        self.ankle = f"{side}_ankle"
        self.ankle_y_hist = deque(maxlen=5)
        self.ukf = ukf

    def _is_swing(self, world_landmarks):
        ankle = world_landmarks.get(self.ankle)
        if not ankle:
            return False
        self.ankle_y_hist.append(ankle[1])
        if len(self.ankle_y_hist) < 3:
            return False
        vy = self.ankle_y_hist[-1] - self.ankle_y_hist[0]
        return abs(vy) > 0.03

    def compute(self, world_landmarks, image_landmarks, visibility):
        heel = world_landmarks.get(self.heel)
        foot_idx = world_landmarks.get(self.foot_index)
        if not heel or not foot_idx or not self._is_swing(world_landmarks):
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
            }

        f = np.array([foot_idx[0] - heel[0], foot_idx[2] - heel[2]])
        if np.linalg.norm(f) < 0.01:
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
            }

        yaw = np.arctan2(-f[1], -f[0])

        if self.ukf:
            yaw = self.ukf.update(yaw)

        # Continuous EMA recalibration
        corrected = self.apply_ema_bias(yaw)

        threshold = 0.15
        conf = min(
            1.0, visibility.get(self.heel, 0) * visibility.get(self.foot_index, 0)
        )
        if abs(corrected) < threshold:
            likelihood = 0.0
            rot_side = "none"
        else:
            likelihood = min(1.0, abs(corrected) / 0.5)
            rot_side = "left" if corrected > 0 else "right"
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": rot_side,
            "confidence": conf,
        }
