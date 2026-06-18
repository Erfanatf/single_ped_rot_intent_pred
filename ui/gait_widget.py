from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from gait.phase_detector import GaitPhaseDetector
from PySide6.QtCore import Qt

class GaitWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gait_detector = GaitPhaseDetector()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)

        self.label_left = QLabel("Left: swing")
        self.label_right = QLabel("Right: swing")
        for lbl in (self.label_left, self.label_right):
            lbl.setAlignment(Qt.AlignLeft)
            lbl.setStyleSheet("font-size: 16px; color: #e0e0e0; padding: 4px;")
        layout.addWidget(self.label_left)
        layout.addWidget(self.label_right)
        self.setLayout(layout)

    def update_phase(self, phases):
        self.label_left.setText(f"Left: {phases['left']}")
        self.label_right.setText(f"Right: {phases['right']}")
        # color coding
        if phases['left'] == 'stance':
            self.label_left.setStyleSheet("font-size: 16px; color: #4caf50; padding: 4px;")
        else:
            self.label_left.setStyleSheet("font-size: 16px; color: #ffab40; padding: 4px;")
        if phases['right'] == 'stance':
            self.label_right.setStyleSheet("font-size: 16px; color: #4caf50; padding: 4px;")
        else:
            self.label_right.setStyleSheet("font-size: 16px; color: #ffab40; padding: 4px;")