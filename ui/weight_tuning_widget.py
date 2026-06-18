from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QScrollArea
from PySide6.QtCore import Qt

class WeightTuningWidget(QWidget):
    def __init__(self, feature_names, initial_weights=None, parent=None):
        super().__init__(parent)
        self.feature_names = feature_names
        self.sliders = {}
        self.labels = {}
        self.weight_labels = {}

        # Wrap in a scroll area for many features
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)

        for name in self.feature_names:
            row = QVBoxLayout()
            # Label
            lbl = QLabel(name.replace('_', ' ').title())
            lbl.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            row.addWidget(lbl)

            # Slider (0-100)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            # Set initial value
            init_w = initial_weights.get(name, 1.0) if initial_weights else 1.0
            slider.setValue(int(init_w * 20))   # scale: weight*20 = slider value (max 5.0 -> 100)
            slider.valueChanged.connect(self._on_slider_changed)
            row.addWidget(slider)

            # Current weight display
            w_lbl = QLabel(f"{init_w:.1f}")
            w_lbl.setStyleSheet("color: #aaa; font-size: 10px;")
            row.addWidget(w_lbl)

            layout.addLayout(row)
            self.sliders[name] = slider
            self.labels[name] = lbl
            self.weight_labels[name] = w_lbl

        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Callback for external update
        self.callback = None

    def _on_slider_changed(self, val):
        sender = self.sender()
        for name, slider in self.sliders.items():
            if slider == sender:
                w = val / 20.0   # map 0-100 to 0.0-5.0
                self.weight_labels[name].setText(f"{w:.1f}")
                if self.callback:
                    self.callback(name, w)
                break

    def set_callback(self, func):
        self.callback = func

    def get_weights(self):
        """Return current weight dict."""
        return {name: self.sliders[name].value() / 20.0 for name in self.feature_names}