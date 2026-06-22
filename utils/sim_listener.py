import json
import socket
import threading
import numpy as np

class SimListener:
    def __init__(self, host="127.0.0.1", port=9998):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(0.5)
        self.lock = threading.Lock()
        self.data = {}
        self.running = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self):
        while self.running:
            try:
                msg, _ = self.sock.recvfrom(65536)
                state = json.loads(msg.decode())
                with self.lock:
                    self.data = state
            except socket.timeout:
                continue
            except Exception:
                pass

    def get_state(self):
        with self.lock:
            return self.data.copy()

    def stop(self):
        self.running = False
        self.sock.close()