from abc import ABC, abstractmethod


class BaseFeature(ABC):
    def __init__(self, name: str, ema_alpha=0.1):
        self.name = name
        self.ema_alpha = ema_alpha
        self.ema = 0.0  # exponential moving average of raw values
        self.calibrated = False

    @abstractmethod
    def compute(
        self, world_landmarks: dict, image_landmarks: dict, visibility: dict
    ) -> dict:
        pass

    def apply_ema_bias(self, raw_value):
        """Update EMA and return bias‑corrected value."""
        self.ema = self.ema_alpha * raw_value + (1 - self.ema_alpha) * self.ema
        return raw_value - self.ema

    def set_ema(self, value):
        """Force the EMA to a specific value (manual calibration)."""
        self.ema = value
        self.calibrated = True
