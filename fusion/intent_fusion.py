import numpy as np
from collections import deque

class IntentFusion:
    def __init__(self, weights=None, ema_alpha=0.2, debounce_frames=5):
        self.weights = weights or {}
        self.ema_alpha = ema_alpha
        self.debounce_frames = debounce_frames

        # Smoothed scores
        self.smooth_left = 0.0
        self.smooth_right = 0.0

        # Debounce state
        self.current_intent = "Straight"
        self.pending_intent = "Straight"
        self.pending_counter = 0

    def predict(self, feature_data: dict) -> dict:
        left_score = 0.0
        right_score = 0.0
        total_weight = 0.0

        for name, data in feature_data.items():
            if data.get('side', 'none') == 'none':
                continue
            lik = data.get('rotation_likelihood', 0.0)
            if lik <= 0:
                continue
            w = self.weights.get(name, 1.0)
            side = data['side']
            if side == 'left':
                left_score += w * lik
            elif side == 'right':
                right_score += w * lik
            total_weight += w

        if total_weight == 0:
            left_norm = 0.0
            right_norm = 0.0
        else:
            left_norm = left_score / total_weight
            right_norm = right_score / total_weight

        # EMA smoothing
        self.smooth_left = self.ema_alpha * left_norm + (1 - self.ema_alpha) * self.smooth_left
        self.smooth_right = self.ema_alpha * right_norm + (1 - self.ema_alpha) * self.smooth_right

        # Determine raw intent from smoothed scores
        diff = self.smooth_left - self.smooth_right
        threshold = 0.05   # minimum difference to declare a side
        if diff > threshold:
            raw_intent = "Rotate Left"
            confidence = min(1.0, diff * 3.0)   # scale difference to 0-1
        elif diff < -threshold:
            raw_intent = "Rotate Right"
            confidence = min(1.0, -diff * 3.0)
        else:
            raw_intent = "Straight"
            confidence = 0.0

        # Debounce
        if raw_intent == self.current_intent:
            self.pending_intent = self.current_intent
            self.pending_counter = 0
        else:
            if raw_intent == self.pending_intent:
                self.pending_counter += 1
                if self.pending_counter >= self.debounce_frames:
                    self.current_intent = raw_intent
                    self.pending_counter = 0
            else:
                self.pending_intent = raw_intent
                self.pending_counter = 1

        return {
            'intent': self.current_intent,
            'confidence': confidence if self.current_intent != "Straight" else 0.0,
            'raw_score': diff,
            'left_score': self.smooth_left,
            'right_score': self.smooth_right
        }