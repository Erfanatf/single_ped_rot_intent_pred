import time
from collections import deque

class RollingBuffer:
    def __init__(self, duration_sec: float):
        self.duration = duration_sec
        self.buffer = deque()   # each element: (timestamp, data_dict)

    def add(self, data: dict):
        now = time.time()
        self.buffer.append((now, data))
        self._expire(now)

    def _expire(self, current_time):
        while self.buffer and current_time - self.buffer[0][0] > self.duration:
            self.buffer.popleft()

    def get_recent(self):
        """Return all buffered data as list of dicts with 'timestamp' key added."""
        result = []
        for ts, d in self.buffer:
            d_copy = d.copy()
            d_copy['timestamp'] = ts
            result.append(d_copy)
        return result

    def clear(self):
        self.buffer.clear()