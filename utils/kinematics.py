import time
from collections import deque

class RotationKinematics:
    def __init__(self, scale=2.0, ema_alpha=0.2):
        self.scale = scale                     # rad/s per unit of fused net score per second
        self.ema_alpha = ema_alpha
        self.last_signal = None
        self.last_time = None
        self.angular_velocity = 0.0
        self.angular_acceleration = 0.0
        self.prev_velocity = 0.0

    def update(self, signal_value, timestamp_s):
        if self.last_signal is None:
            self.last_signal = signal_value
            self.last_time = timestamp_s
            return 0.0, 0.0

        dt = timestamp_s - self.last_time
        if dt <= 0:
            # time didn't advance – skip update
            return self.angular_velocity, self.angular_acceleration

        # Instantaneous signal derivative
        # raw_velocity = (signal_value - self.last_signal) / dt
        raw_velocity = signal_value
        
        # Exponential smoothing of angular velocity
        if self.angular_velocity is None:
            self.angular_velocity = raw_velocity
        else:
            self.angular_velocity = (self.ema_alpha * raw_velocity +
                                     (1 - self.ema_alpha) * self.angular_velocity)

        # Acceleration from change in smoothed velocity
        self.angular_acceleration = (self.angular_velocity - self.prev_velocity) / dt
        self.prev_velocity = self.angular_velocity

        # Apply scaling to physical units (rad/s, rad/s²)
        vel_phys = self.angular_velocity * self.scale
        acc_phys = self.angular_acceleration * self.scale

        # Store current for next call
        self.last_signal = signal_value
        self.last_time = timestamp_s

        return vel_phys, acc_phys