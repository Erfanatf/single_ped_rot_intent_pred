import sys
import time
import yaml
import argparse
import cv2
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from extractors.mediapipe_full import MediaPipeFullExtractor
from extractors.yolo_full import YOLOFullExtractor
from utils.threaded_detector import ThreadedDetector
from utils.ukf import UKF1D
from utils.kalman import KeypointTrackerCoordinator   # <-- new

from features.torso_pelvis_torsion import TorsoPelvisTorsion
from features.foot_progression import FootProgressionDifference
from features.step_width import StepWidth
from features.swing_foot_orientation import SwingFootOrientation
from features.pelvis_yaw import PelvisYaw
from features.hip_rotation import HipRotation
from features.shoulder_yaw import ShoulderYaw
from features.head_yaw import HeadYaw
from features.com_shift import ComShift
from features.arm_swing_asymmetry import ArmSwingAsymmetry

from buffer.rolling_buffer import RollingBuffer
from ui.dashboard import Dashboard
from recording.logger import FeatureLogger
from recording.screen_recorder import ScreenRecorder

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class MainController:
    def __init__(self, config, model):
        self.config = config
        self.cap = cv2.VideoCapture(config.get('camera_id', 0))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['frame_width'])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['frame_height'])

        if model == 'mediapipe':
            extractor = MediaPipeFullExtractor(config)
        else:
            extractor = YOLOFullExtractor(config)

        self.detector = ThreadedDetector(extractor,
                                         (config['inference_width'], config['inference_height']),
                                         config['display_downscale'])
        self.detector.start()

        # ---------- Optional keypoint Kalman filter ----------
        self.kp_filter = None
        if config.get('keypoint_filter', False):
            self.kp_filter = KeypointTrackerCoordinator(
                dt=config.get('keypoint_filter_dt', 0.033),
                process_noise=config.get('keypoint_process_noise', 0.001),
                measurement_noise=config.get('keypoint_measurement_noise', 0.01),
                max_missing=config.get('keypoint_max_missing', 10)
            )

        # UKF per feature (kept as is)
        ukf_torsion = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_foot_diff = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_step_width = UKF1D(process_noise=0.001, measurement_noise=0.01)
        ukf_swing_left = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_swing_right = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_pelvis = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_hip_left = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_hip_right = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_shoulder = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_head = UKF1D(process_noise=0.01, measurement_noise=0.1)
        ukf_com = UKF1D(process_noise=0.01, measurement_noise=0.001)    
        ukf_arm = UKF1D(process_noise=0.01, measurement_noise=0.1)

        self.features = [
            TorsoPelvisTorsion(ukf=ukf_torsion),
            FootProgressionDifference(ukf=ukf_foot_diff),
            StepWidth(ukf=ukf_step_width),
            # SwingFootOrientation('left', ukf=ukf_swing_left),
            # SwingFootOrientation('right', ukf=ukf_swing_right),
            PelvisYaw(ukf=ukf_pelvis),
            # HipRotation('left', ukf=ukf_hip_left),
            # HipRotation('right', ukf=ukf_hip_right),
            ShoulderYaw(ukf=ukf_shoulder),
            HeadYaw(ukf=ukf_head),
            ComShift(ukf=ukf_com),
            ArmSwingAsymmetry(ukf=ukf_arm),
        ]

        self.buffer = RollingBuffer(config['buffer_duration'])
        self.dashboard = Dashboard(self.detector, self.features, self.buffer, config)
        self.dashboard.show()

        self.logger = FeatureLogger(config['output_dir']) if config.get('save_history') else None
        self.recorder = ScreenRecorder(config['output_dir']) if config.get('record_screen') else None
        if self.recorder:
            self.recorder.start(self.dashboard)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(33)
        QApplication.instance().aboutToQuit.connect(self.cleanup)

    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        ds = self.config.get('display_downscale', 1.0)
        if ds != 1.0:
            display_frame = cv2.resize(frame, None, fx=ds, fy=ds)
        else:
            display_frame = frame.copy()
        dh, dw = display_frame.shape[:2]
        self.detector.set_display_size(dw, dh)
        self.detector.update_frame(frame)
        _, img_lm, world_lm, vis = self.detector.get_latest_data()

        # Apply keypoint filter if enabled
        if self.kp_filter and world_lm:
            world_lm = self.kp_filter.step(world_lm)

        # The dashboard’s compute_features uses detector.get_latest_data() internally.
        # We must give it the filtered landmarks somehow.
        # Modify dashboard to accept an optional override dict.
        # Simple solution: set a variable that dashboard reads.
        self.dashboard.filtered_world_lm = world_lm   # custom attribute

        self.dashboard.camera_widget.show_frame(display_frame, img_lm)
        if self.logger and self.dashboard.current_features:
            self.logger.log(time.time(), self.dashboard.current_features)
        if self.recorder:
            self.recorder.record_frame()

    def cleanup(self):
        self.detector.stop()
        self.cap.release()
        if self.logger:
            self.logger.close()
        if self.recorder:
            self.recorder.stop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--model', choices=['mediapipe', 'yolo'])
    args = parser.parse_args()
    config = load_config(args.config)
    model = args.model or config.get('model', 'mediapipe')
    app = QApplication(sys.argv)
    controller = MainController(config, model)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()