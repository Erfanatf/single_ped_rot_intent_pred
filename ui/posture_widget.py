from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from posture.classifier import PostureClassifier
from PySide6.QtCore import Qt

class PostureWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.posture_classifier = PostureClassifier()
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        self.label = QLabel("Posture: unknown")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 18px; color: #ffffff; background-color: #2a2a3c; border-radius: 8px; padding: 8px;")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_posture(self, posture):
        self.label.setText(f"Posture: {posture.replace('_', ' ').title()}")