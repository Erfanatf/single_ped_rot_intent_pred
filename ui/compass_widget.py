import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QRect

class CompassWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.raw_score = 0.0          # negative = right, positive = left
        self.intent_text = "Straight"
        self.confidence = 0.0

    def update_direction(self, raw_score: float):
        """Update with continuous raw score from fusion."""
        self.raw_score = max(-1.0, min(1.0, raw_score))
        # Determine intent label
        if abs(self.raw_score) < 0.1:
            self.intent_text = "Straight"
            self.confidence = 0.0
        elif self.raw_score > 0:
            self.intent_text = "Rotate Left"
            self.confidence = self.raw_score
        else:
            self.intent_text = "Rotate Right"
            self.confidence = abs(self.raw_score)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(cx, cy) - 20

        # Background circle
        painter.setPen(QPen(QColor("#3a3a4c"), 3))
        painter.setBrush(QColor("#1e1e2f"))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Compass markings
        painter.setFont(QFont("Arial", 10))
        for angle_deg, label in [(0, "↑"), (90, "→"), (180, "↓"), (270, "←")]:
            rad = math.radians(angle_deg - 90)   # 0 at top
            x = cx + math.cos(rad) * (radius - 15)
            y = cy + math.sin(rad) * (radius - 15)
            painter.setPen(QPen(QColor("#888888"), 1))
            painter.drawText(int(x) - 10, int(y) + 5, label)

        # Needle: raw_score > 0 = left turn -> point left (negative angle)
        angle_deg = -self.raw_score * 90.0
        needle_len = radius - 30
        rad = math.radians(angle_deg - 90)   # 0 at top
        nx = cx + math.cos(rad) * needle_len
        ny = cy + math.sin(rad) * needle_len
        painter.setPen(QPen(QColor("cyan"), 3))
        painter.drawLine(cx, cy, int(nx), int(ny))

        # Text
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.setPen(QPen(QColor("white")))
        text = f"{self.intent_text} ({self.confidence:.2f})"
        painter.drawText(QRect(10, h - 30, w - 20, 20), Qt.AlignCenter, text)