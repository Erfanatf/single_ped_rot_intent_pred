import sys
import time
import yaml
import argparse
import cv2
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from extractors.mediapipe_full import MediaPipeFullExtractor
from extractors.yolo_full import YOLOFullExtractor
from ui.sim_view_widget import SimViewWidget
from utils.omega_sender import OmegaSender
from utils.sim_listener import SimListener
from utils.threaded_detector import ThreadedDetector
from utils.ukf import UKF1D
from utils.kalman import KeypointTrackerCoordinator
from utils.mjpeg_reader import MJPEGReader

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
from utils.kinematics import RotationKinematics

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class MainController:
    def __init__(self, config, model, source_override=None, user=None, password=None):
        self.config = config

        # --- Determine source type (webcam, video file, or network stream) ---
        if source_override is not None:
            source = str(source_override)
        else:
            source = str(config.get('camera_id', 0))

        network_prefixes = ('http://', 'https://', 'rtsp://', 'rtmp://')
        self.is_network = source.startswith(network_prefixes)
        self.mjpeg_reader = None   # only used for HTTP MJPEG streams

        if self.is_network:
            # --- Temporarily clear ALL proxy environment variables ---
            old_env = {}
            for var in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
                        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY'):
                old_env[var] = os.environ.pop(var, None)

            if source.startswith(('http://', 'https://')):
                # Use our reliable MJPEG reader for HTTP streams
                print(f"Opening MJPEG stream: {source}")
                self.mjpeg_reader = MJPEGReader(source, username=user, password=password)
                self.mjpeg_reader.start()
                self.cap = None   # we don't use OpenCV for this stream
                self.is_video_file = False
            else:
                # RTSP/RTMP streams still use OpenCV (with proxy cleared)
                self.cap = cv2.VideoCapture(source)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.is_video_file = False

            # Restore proxy settings for other parts of the program
            for var, value in old_env.items():
                if value is not None:
                    os.environ[var] = value

        elif source.isdigit():
            camera_id = int(source)
            self.cap = cv2.VideoCapture(camera_id)
            self.is_video_file = False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['frame_width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['frame_height'])
        else:
            self.cap = cv2.VideoCapture(source)
            self.is_video_file = True

        # --- Rest of init (unchanged) ---
        if model == 'mediapipe':
            extractor = MediaPipeFullExtractor(config)
        else:
            extractor = YOLOFullExtractor(config)

        self.detector = ThreadedDetector(extractor,
                                         (config['inference_width'], config['inference_height']),
                                         config['display_downscale'])
        self.detector.start()

        self.kp_filter = None
        if config.get('keypoint_filter', False):
            self.kp_filter = KeypointTrackerCoordinator(
                dt=config.get('keypoint_filter_dt', 0.033),
                process_noise=config.get('keypoint_process_noise', 0.001),
                measurement_noise=config.get('keypoint_measurement_noise', 0.01),
                max_missing=config.get('keypoint_max_missing', 10)
            )

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
        # ukf_com = UKF1D(process_noise=0.01, measurement_noise=0.001)
        # ukf_arm = UKF1D(process_noise=0.01, measurement_noise=0.1)

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
            # ComShift(ukf=ukf_com),
            # ArmSwingAsymmetry(ukf=ukf_arm),
        ]

        kin_scale = config.get('kinematics_scale', 2.0)
        self.kinematics = RotationKinematics(scale=kin_scale)
        self.omega_sender = OmegaSender()
        if config.get('send_omega', False):
            self.omega_sender.start()
            
        self.buffer = RollingBuffer(config['buffer_duration'])
        self.dashboard = Dashboard(self.detector, self.features, self.buffer, config, kinematics=self.kinematics)
        self.sim_listener = SimListener()
        self.sim_listener.start()
        self.sim_view = SimViewWidget()
        self.dashboard.add_sim_view(self.sim_view)
        
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
        # Get frame from the appropriate source
        if self.mjpeg_reader is not None:
            ret, frame = self.mjpeg_reader.read()
        else:
            ret, frame = self.cap.read()

        if not ret:
            if self.is_video_file:
                print("Video ended.")
            elif self.is_network:
                print("Network stream interrupted.")
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

        if self.kp_filter and world_lm:
            world_lm = self.kp_filter.step(world_lm)

        self.dashboard.filtered_world_lm = world_lm
        self.dashboard.camera_widget.show_frame(display_frame, img_lm)
        if self.logger and self.dashboard.current_features:
            ang_vel, ang_acc = self.dashboard.latest_kinematics
            self.omega_sender.update_omega(ang_vel)   # send the current ω
            extra = {'angular_velocity': ang_vel, 'angular_acceleration': ang_acc}
            self.logger.log(time.time(), self.dashboard.current_features, extra=extra)
        if self.recorder:
            self.recorder.record_frame()
        
        # Update simulator view
        state = self.sim_listener.get_state()
        if state:
            self.sim_view.update_state(state)

    def cleanup(self):
        self.detector.stop()
        if self.mjpeg_reader:
            self.mjpeg_reader.release()
        if self.cap:
            self.cap.release()
        if self.logger:
            self.logger.close()
        if self.recorder:
            self.recorder.stop()

def main():
    parser = argparse.ArgumentParser(description="Human Rotation Intent Detector")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--model', choices=['mediapipe', 'yolo'], help='Override model from config')
    parser.add_argument('--source', type=str, default=None,
                        help='Video source: camera index (0), video file path (walk.mp4), or network URL (http://...)')
    parser.add_argument('--user', type=str, default=None, help='Username for network stream authentication')
    parser.add_argument('--password', type=str, default=None, help='Password for network stream authentication')
    args = parser.parse_args()
    config = load_config(args.config)
    model = args.model or config.get('model', 'mediapipe')

    app = QApplication(sys.argv)
    controller = MainController(config, model, source_override=args.source, user=args.user, password=args.password)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()