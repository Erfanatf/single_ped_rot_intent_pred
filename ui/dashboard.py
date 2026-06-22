import math
import sys
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QPushButton,
                               QWidget, QVBoxLayout, QSplitter)
from PySide6.QtCore import Qt, QTimer
from .camera_widget import CameraWidget
from .plot_widget import PlotWidget
from .gait_widget import GaitWidget
from .posture_widget import PostureWidget
from .compass_widget import CompassWidget
from fusion.intent_fusion import IntentFusion
from .weight_tuning_widget import WeightTuningWidget

STYLE = """
QMainWindow {
    background-color: #1e1e2f;
}
QDockWidget {
    color: #e0e0e0;
    background-color: #2a2a3c;
    border: 1px solid #3a3a4c;
    font-size: 14px;
}
QDockWidget::title {
    background-color: #3a3a4c;
    padding: 6px;
    font-weight: bold;
}
QLabel {
    color: #e0e0e0;
    font-size: 14px;
}
QSplitter::handle {
    background-color: #3a3a4c;
    width: 2px;
}
"""

class Dashboard(QMainWindow):
    def __init__(self, detector, feature_extractors, buffer, config, kinematics=None):
        super().__init__()
        self.detector = detector
        self.feature_extractors = feature_extractors
        self.buffer = buffer
        self.config = config
        self.kinematics = kinematics
        self.latest_kinematics = (0.0, 0.0)
        self.current_features = {}
        self.filtered_world_lm = None

        fusion_weights = config.get('fusion_weights', {})
        self.fusion = IntentFusion(weights=fusion_weights)

        self.setStyleSheet(STYLE)
        self.setWindowTitle("Rotation Intent Predictor")
        self.setMinimumSize(1800, 1000)

        # ---- Central splitter (Camera top, Sim View bottom) ----
        self.central_splitter = QSplitter(Qt.Vertical)
        self.camera_widget = CameraWidget(self)
        self.central_splitter.addWidget(self.camera_widget)
        # Sim view placeholder – added later via add_sim_view
        self.sim_view_placeholder = QWidget()
        self.central_splitter.addWidget(self.sim_view_placeholder)
        self.central_splitter.setSizes([400, 300])
        self.setCentralWidget(self.central_splitter)

        # ---- Plot dock (right, 2 columns) ----
        plot_features = [feat.name for feat in self.feature_extractors] + \
                        ['angular_velocity', 'angular_acceleration']
        self.plot_widget = PlotWidget(self, plot_features,
                                      buffer_duration=config.get('buffer_duration', 4.0),
                                      cols=2)  # ← 2 columns instead of 3
        plot_dock = QDockWidget("Biomechanical Features", self)
        plot_dock.setWidget(self.plot_widget)
        plot_dock.setMinimumWidth(600)
        self.addDockWidget(Qt.RightDockWidgetArea, plot_dock)
        self.resizeDocks([plot_dock], [650], Qt.Horizontal)

        # ---- Compass dock (top-left) ----
        self.compass_widget = CompassWidget(self)
        compass_dock = QDockWidget("Rotation Intent", self)
        compass_dock.setWidget(self.compass_widget)
        compass_dock.setMinimumWidth(220)
        self.addDockWidget(Qt.LeftDockWidgetArea, compass_dock)

        # ---- Weight tuning dock (left, below compass) ----
        initial_weights = config.get('fusion_weights', {})
        self.weight_widget = WeightTuningWidget(
            [feat.name for feat in self.feature_extractors],
            initial_weights=initial_weights
        )
        self.weight_widget.set_callback(self._update_weight)
        weight_dock = QDockWidget("Fusion Weights", self)
        weight_dock.setWidget(self.weight_widget)
        weight_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.LeftDockWidgetArea, weight_dock)

        # ---- Gait dock (bottom-left) ----
        self.gait_widget = GaitWidget(self)
        gait_dock = QDockWidget("Gait Phase", self)
        gait_dock.setWidget(self.gait_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, gait_dock)

        # ---- Posture dock (bottom-right) ----
        self.posture_widget = PostureWidget(self)
        posture_dock = QDockWidget("Body Orientation", self)
        posture_dock.setWidget(self.posture_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, posture_dock)

        # ---- Feature computation timer ----
        self.feature_timer = QTimer()
        self.feature_timer.timeout.connect(self.compute_features)
        self.feature_timer.start(50)

        # ---- Calibration button ----
        self.calibrate_btn = QPushButton("🔄 Calibrate Neutral")
        self.calibrate_btn.setStyleSheet("background: #3a3a4c; color: white; padding: 6px;")
        self.calibrate_btn.clicked.connect(self.start_calibration)
        calibrate_dock = QDockWidget("Calibration", self)
        calibrate_dock.setWidget(self.calibrate_btn)
        self.addDockWidget(Qt.TopDockWidgetArea, calibrate_dock)

        self.calibration_samples = []
        self.calibrating = False
        self.calibration_start_time = 0

    def add_sim_view(self, widget):
        """Replace the placeholder with the actual sim view widget."""
        # Find the placeholder index
        idx = self.central_splitter.indexOf(self.sim_view_placeholder)
        self.central_splitter.replaceWidget(idx, widget)
        self.sim_view_placeholder = widget

    def start_calibration(self):
        self.calibration_samples = []
        self.calibrating = True
        self.calibration_start_time = time.time()
        self.calibrate_btn.setText("⏳ Calibrating...")
        self.calibrate_btn.setEnabled(False)

    def finish_calibration(self):
        if not self.calibration_samples:
            return
        emas = {}
        for key in self.calibration_samples[0].keys():
            vals = [s[key] for s in self.calibration_samples if key in s]
            if vals:
                emas[key] = sum(vals) / len(vals)
        for feat in self.feature_extractors:
            if feat.name in emas:
                feat.set_ema(emas[feat.name])
        self.calibrating = False
        self.calibrate_btn.setText("✅ Calibrated")
        self.calibrate_btn.setEnabled(True)

    def compute_features(self):
        _, img_lm, world_lm, vis = self.detector.get_latest_data()
        if self.filtered_world_lm is not None:
            world_lm = self.filtered_world_lm
        if not world_lm:
            return

        feature_data = {}
        for feat in self.feature_extractors:
            try:
                res = feat.compute(world_lm, img_lm, vis)
            except Exception as e:
                print(f"Feature {feat.name} failed: {e}")
                res = {'value': 0.0, 'rotation_likelihood': 0.0, 'side': 'none',
                       'confidence': 0.0, 'raw_value': 0.0}
            feature_data[feat.name] = res

        if self.calibrating:
            self.calibration_samples.append(
                {name: res.get('raw_value', res['value']) for name, res in feature_data.items()}
            )
            if time.time() - self.calibration_start_time > 2.0:
                self.finish_calibration()
            return

        self.current_features = feature_data
        self.buffer.add(feature_data)
        self.plot_widget.update_plots(self.buffer.get_recent(), current_time=time.time())

        fused = self.fusion.predict(feature_data)
        raw_score = fused['raw_score']

        now = time.time()
        if self.kinematics is not None:
            ang_vel, ang_acc = self.kinematics.update(raw_score, now)
            self.latest_kinematics = (ang_vel, ang_acc)
            feature_data['angular_velocity'] = {
                'value': ang_vel, 'rotation_likelihood': 0.0,
                'side': 'none', 'confidence': 1.0, 'raw_value': ang_vel
            }
            feature_data['angular_acceleration'] = {
                'value': ang_acc, 'rotation_likelihood': 0.0,
                'side': 'none', 'confidence': 1.0, 'raw_value': ang_acc
            }
        else:
            ang_vel, ang_acc = 0.0, 0.0

        self.compass_widget.update_direction(raw_score, ang_vel, ang_acc)

        try:
            gait_phase = self.gait_widget.gait_detector.update(world_lm, img_lm, vis)
            self.gait_widget.update_phase(gait_phase)
        except Exception as e:
            print(f"Gait update failed: {e}")

        try:
            posture = self.posture_widget.posture_classifier.classify(img_lm, vis)
            self.posture_widget.update_posture(posture)
        except Exception as e:
            print(f"Posture update failed: {e}")

    def _update_weight(self, name, value):
        self.fusion.weights[name] = value