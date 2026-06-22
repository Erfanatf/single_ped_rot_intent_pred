import numpy as np
from .base_feature import BaseFeature


class FootProgressionDifference(BaseFeature):
    def __init__(self, ukf=None, fixed_threshold=0.01, ema_alpha=0.1):
        super().__init__("foot_progression_difference", ema_alpha)
        self.ukf = ukf
        self.threshold = fixed_threshold

    def compute(self, world_landmarks, image_landmarks, visibility):
        left_heel = world_landmarks.get("left_heel")
        left_foot_idx = world_landmarks.get("left_foot_index")
        left_ankle = world_landmarks.get("left_ankle")
        right_heel = world_landmarks.get("right_heel")
        right_foot_idx = world_landmarks.get("right_foot_index")
        right_ankle = world_landmarks.get("right_ankle")

        if not all(
            [
                left_heel,
                left_foot_idx,
                left_ankle,
                right_heel,
                right_foot_idx,
                right_ankle,
            ]
        ):
            return {
                "value": 0.0,
                "rotation_likelihood": 0.0,
                "side": "none",
                "confidence": 0.0,
                "raw_value": 0.0,
            }

        if left_ankle[2] < right_ankle[2]:
            front_side = "left"
        else:
            front_side = "right"

        left_vec = np.array(
            [left_foot_idx[0] - left_heel[0], left_foot_idx[2] - left_heel[2]]
        )
        right_vec = np.array(
            [right_foot_idx[0] - right_heel[0], right_foot_idx[2] - right_heel[2]]
        )

        yaw_left = np.arctan2(-left_vec[1], -left_vec[0])
        yaw_right = np.arctan2(-right_vec[1], -right_vec[0])

        if front_side == "left":
            raw_diff = yaw_left - 0.0
        else:
            raw_diff = yaw_right - 0.0

        if self.ukf:
            filtered_diff = self.ukf.update(raw_diff)
        else:
            filtered_diff = raw_diff

        raw_val = filtered_diff
        corrected = self.apply_ema_bias(raw_val)

        conf = min(
            visibility.get("left_heel", 1.0),
            visibility.get("left_foot_index", 1.0),
            visibility.get("right_heel", 1.0),
            visibility.get("right_foot_index", 1.0),
        )
        thr = self.threshold
        if abs(corrected) < thr:
            likelihood = 0.0
            side = "none"
        else:
            likelihood = min(1.0, (abs(corrected)/thr))
            side = "left" if corrected > 0 else "right"
        likelihood *= conf
        return {
            "value": corrected,
            "rotation_likelihood": likelihood,
            "side": side,
            "confidence": conf,
            "raw_value": raw_val,
        }
