import numpy as np
from collections import defaultdict

class KeypointKalmanFilter:
    """6‑state Kalman filter (pos_x, pos_y, pos_z, vel_x, vel_y, vel_z) for one keypoint."""
    def __init__(self, dt=1/30., process_noise=0.001, measurement_noise=0.01):
        self.dt = dt
        self.x = np.zeros(6)
        # State transition: pos += vel*dt, vel unchanged
        self.F = np.eye(6)
        self.F[0, 3] = dt
        self.F[1, 4] = dt
        self.F[2, 5] = dt
        # Measurement matrix: observe position only
        self.H = np.zeros((3, 6))
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0
        self.P = np.eye(6) * 1.0
        self.Q = np.eye(6) * process_noise
        self.R = np.eye(3) * measurement_noise
        self.initialised = False
        self.frames_since_update = 0

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.frames_since_update += 1

    def update(self, measurement):
        # measurement: [x, y, z] or None
        if measurement is None or any(np.isnan(measurement)):
            return self.x[:3]   # return predicted position

        z = np.array(measurement)
        if not self.initialised:
            self.x[:3] = z
            self.initialised = True
            self.frames_since_update = 0
            return self.x[:3]

        # Innovation
        y = z - (self.H @ self.x)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = self.P - K @ self.H @ self.P
        self.frames_since_update = 0
        return self.x[:3]

class KeypointTrackerCoordinator:
    def __init__(self, dt=1/30., process_noise=0.001, measurement_noise=0.01, max_missing=10):
        self.dt = dt
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.max_missing = max_missing
        self.trackers = {}

    def step(self, world_landmarks):
        """
        world_landmarks: dict {name: [x, y, z]}  (raw from MediaPipe)
        Returns filtered dict in same format.
        """
        filtered = {}
        # Predict all existing trackers
        for name in list(self.trackers.keys()):
            self.trackers[name].predict()
            if self.trackers[name].frames_since_update > self.max_missing:
                del self.trackers[name]

        # Update with measurements (if present)
        if world_landmarks:
            for name, pos in world_landmarks.items():
                if name not in self.trackers:
                    self.trackers[name] = KeypointKalmanFilter(
                        dt=self.dt,
                        process_noise=self.process_noise,
                        measurement_noise=self.measurement_noise
                    )
                filtered[name] = self.trackers[name].update(pos).tolist()

        # For trackers that did not get a measurement, return prediction
        for name, tracker in self.trackers.items():
            if name not in filtered:
                filtered[name] = tracker.x[:3].tolist()

        return filtered