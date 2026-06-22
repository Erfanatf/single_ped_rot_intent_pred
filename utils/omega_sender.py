import socket
import threading

class OmegaSender:
    def __init__(self, host="127.0.0.1", port=9999):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.port = port
        self.lock = threading.Lock()
        self.omega = 0.0

    def update_omega(self, omega):
        with self.lock:
            self.omega = omega

    def send_once(self):
        with self.lock:
            msg = f"{self.omega:.6f}".encode()
        try:
            self.sock.sendto(msg, (self.host, self.port))
        except Exception:
            pass   # silently ignore network errors

    def start(self, interval=0.05):
        """Start periodic sending in a daemon thread."""
        def _send_loop():
            while True:
                self.send_once()
                threading.Event().wait(interval)
        t = threading.Thread(target=_send_loop, daemon=True)
        t.start()