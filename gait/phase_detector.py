import numpy as np
from collections import deque

class GaitPhaseDetector:
    def __init__(self, threshold=0.015, window=10):
        self.threshold = threshold
        self.history = {'left': deque(maxlen=window), 'right': deque(maxlen=window)}
        self.phase = {'left': 'stance', 'right': 'stance'}

    def update(self, world_landmarks, image_landmarks, visibility):
        for side in ['left', 'right']:
            ankle = world_landmarks.get(f'{side}_ankle')
            if ankle:
                self.history[side].append(ankle[1])   # Y coordinate
            if len(self.history[side]) >= self.history[side].maxlen:
                # Use a longer window for smoother derivative
                vy = self.history[side][-1] - self.history[side][0]
                if abs(vy) < self.threshold:
                    self.phase[side] = 'stance'
                else:
                    self.phase[side] = 'swing'
            else:
                self.phase[side] = 'stance'   # assume stance until enough data
        return self.phase