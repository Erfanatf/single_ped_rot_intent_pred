import numpy as np
from .base_feature import BaseFeature

class ComShift(BaseFeature):
    def __init__(self, ukf=None, ema_alpha=0.1):
        super().__init__("com_lateral_shift", ema_alpha)
        self.ukf = ukf

    def compute(self, world_landmarks, image_landmarks, visibility):
        lh = world_landmarks.get('left_hip')
        rh = world_landmarks.get('right_hip')
        if not lh or not rh:
            return {'value':0.0, 'rotation_likelihood':0.0, 'side':'none',
                    'confidence':0.0, 'raw_value':0.0}

        com_x = (lh[0] + rh[0]) / 2.0
        raw_val = com_x
        corrected = self.apply_ema_bias(raw_val)

        threshold = 0.04
        conf = min(1.0, visibility.get('left_hip',0)*visibility.get('right_hip',0))
        if abs(corrected) < threshold:
            likelihood = 0.0
            side = 'none'
        else:
            likelihood = min(1.0, abs(corrected)/0.15)
            side = 'left' if corrected > 0 else 'right'
        likelihood *= conf
        return {'value':corrected, 'rotation_likelihood':likelihood,
                'side':side, 'confidence':conf, 'raw_value':raw_val}