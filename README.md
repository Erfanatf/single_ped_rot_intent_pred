# Single Pedestrian Rotation Intent Predictor

Real-time detection of a pedestrian's **rotation intention** (standing straight, turning left, or turning right) from a single RGB camera.  
Uses MediaPipe (or YOLOv8-pose) for full-body keypoints, computes 12 biomechanical features, fuses them with a weighted probabilistic engine, and displays results on a live dashboard with a compass and tunable weights.

---

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Dashboard Overview](#dashboard-overview)
- [Feature Descriptions](#feature-descriptions)
- [Calibration & Adaptation](#calibration-adaptation)
- [Recording & Logging](#recording-logging)
- [References](#references)

---

## Features

- **Multi-model support** – switch between MediaPipe (richest, most robust) and YOLOv8-pose via CLI flag.
- **Full-body 33-point skeleton** – all MediaPipe landmarks plus face, feet, and hands.
- **12 biomechanical features** that detect subtle pre-turn cues:
  - Torso-pelvis torsion
  - Foot progression difference (front foot vs back foot yaw)
  - Step width asymmetry
  - Swing foot orientation (left / right)
  - Shoulder yaw, pelvis yaw, head yaw
  - Hip internal/external rotation (left / right)
  - Centre of mass lateral shift
  - Arm swing asymmetry
- **Unscented Kalman Filters (UKF)** on each feature for noise reduction.
- **Optional keypoint-level Kalman filter** (6-state per landmark) for extra smoothness.
- **Automatic continuous bias adaptation** – the system slowly learns the person's neutral posture and compensates for changes.
- **Manual calibration button** – instantly set the neutral reference by standing still for 2 seconds.
- **Weighted fusion engine** – combines all features with configurable weights (live tunable via sliders).
- **Live dashboard** built with PySide6 + pyqtgraph:
  - Real-time video with skeleton overlay.
  - 3-column grid of feature plots (likelihood + raw value, dual y-axes).
  - Compass widget showing continuous rotation direction and confidence.
  - Gait phase indicator (stance / swing per leg).
  - Body posture classifier (facing camera, back, side, tilted).
  - Fusion weight sliders for real-time tuning.
- **Recording & logging** – save dashboard video and CSV of all feature values with timestamps.

---

## Architecture

```
Camera -> ThreadedDetector (pose extraction on small resolution)
          |
   KeypointFilter (optional) -> smooth world landmarks
          |
   FeatureExtractors (12 independent modules, each with UKF)
          |
   Feature buffer (4-second rolling window)
          |
   IntentFusion (weighted score -> left/right/straight)
          |
   Dashboard (plots, compass, telemetry, sliders)
```

All heavy processing (pose extraction, filtering, feature computation) runs in a background thread, so the UI stays fluid.

---

## Directory Structure

```
single_ped_rot_intent_pred/
├── main.py                     # entry point
├── config.yaml                 # all tunable parameters
├── README.md
├── requirements.txt
├── .gitignore
├── extractors/
│   ├── base.py                 # abstract extractor
│   ├── mediapipe_full.py       # MediaPipe 33-point extractor
│   └── yolo_full.py            # YOLOv8-pose extractor
├── utils/
│   ├── threaded_detector.py    # background pose extraction thread
│   ├── ukf.py                  # 1D Unscented Kalman Filter
│   ├── kalman.py               # keypoint-level Kalman filter bank
│   └── helpers.py              # (geometry utilities)
├── features/                   # 12 biomechanical feature classes
│   ├── base_feature.py
│   ├── torso_pelvis_torsion.py
│   ├── foot_progression.py
│   ├── step_width.py
│   ├── swing_foot_orientation.py
│   ├── shoulder_yaw.py
│   ├── pelvis_yaw.py
│   ├── head_yaw.py
│   ├── hip_rotation.py
│   ├── com_shift.py
│   └── arm_swing_asymmetry.py
├── fusion/
│   └── intent_fusion.py        # weighted score fusion + debounce
├── buffer/
│   └── rolling_buffer.py       # time-based feature buffer
├── gait/
│   └── phase_detector.py       # stance/swing per leg
├── posture/
│   └── classifier.py           # front/back/side classification
├── ui/
│   ├── dashboard.py            # main window, docks, calibration button
│   ├── camera_widget.py        # video display
│   ├── plot_widget.py          # dual-axis feature plots
│   ├── compass_widget.py       # rotation direction compass
│   ├── gait_widget.py          # gait phase display
│   ├── posture_widget.py       # posture label
│   └── weight_tuning_widget.py # live weight sliders
└── recording/
    ├── logger.py               # CSV feature logger
    └── screen_recorder.py      # OpenCV screen recorder
```

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Erfanatf/single_ped_rot_intent_pred.git
cd single_ped_rot_intent_pred
```

### 2. Create a virtual environment (Python 3.10 recommended)
```bash
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate          # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Model files
The repository already includes the required models:
- `pose_landmarker_lite.task` (MediaPipe)
- `yolov8n-pose.pt` (YOLO)

If you want to download them manually:
- MediaPipe: [Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- YOLO: `yolov8n-pose.pt` is automatically downloaded by Ultralytics on first use.

---

## Usage

### Run with MediaPipe (default, recommended)
```bash
python main.py --model mediapipe
```

### Run with YOLOv8
```bash
python main.py --model yolo
```

### Use a custom config file
```bash
python main.py --config path/to/my_config.yaml --model mediapipe
```

### Exit
Press `Ctrl+C` in the terminal or click the close button of the dashboard window.

---

## Configuration

All parameters live in `config.yaml`. Key sections:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `camera_id` | 0 | Camera device index |
| `frame_width` | 640 | Capture width |
| `frame_height` | 480 | Capture height |
| `display_downscale` | 1.0 | Additional display scaling |
| `inference_width` | 320 | Pose model input width |
| `inference_height` | 256 | Pose model input height |
| `model` | mediapipe | Overridden by CLI |
| `buffer_duration` | 4.0 | Feature history length (seconds) |
| `keypoint_filter` | false | Enable keypoint-level Kalman filter |
| `save_history` | true | Log feature values to CSV |
| `record_screen` | false | Record dashboard video |
| `output_dir` | ./recordings | Where recordings and logs go |
| `fusion_weights` | (per-feature) | Weight of each feature in fusion |
| `foot_progression_threshold` | 0.15 | Fixed threshold for foot diff |

---

## Dashboard Overview

When you launch the application, you see:

- **Left dock** – Compass (rotation direction) and Fusion Weight sliders.
- **Central widget** – Live camera feed with full-body skeleton overlay.
- **Right dock** – 3-column grid of feature plots. Each subplot shows:
  - Left y-axis: likelihood (cyan)
  - Right y-axis: raw value (orange)
  - Both auto-scale to keep data visible.
- **Bottom docks** – Gait phase (per leg stance/swing) and Body posture.

### Controls
- **Calibrate Neutral** button: stand still and click; after 2s it sets the current pose as neutral.
- **Weight sliders** – change a feature's influence in real time; the compass updates immediately.
- **Reset Views** (above plots) – restores default zoom on all plots.

---

## Feature Descriptions

All features are computed from MediaPipe's world landmarks (body-centric coordinates).

| Feature | What it measures | Rotation clue |
|---------|------------------|--------------|
| **Torso-Pelvis Torsion** | Angle between shoulder line and hip line | Positive = left turn, negative = right. Very early indicator. |
| **Foot Progression Difference** | Yaw difference between front foot and back foot | The front foot points toward the intended direction. |
| **Shoulder / Pelvis / Head Yaw** | Orientation of each segment relative to neutral | Early directional shift of the upper body. |
| **Hip Rotation** | Internal/external rotation of each thigh | Loading of the inner hip before a turn. |
| **Swing Foot Orientation** | Foot angle during swing phase | Pre-rotation of the foot before landing. |
| **Step Width Asymmetry** | Lateral distance between ankles | Wider base often precedes a turn. |
| **CoM Lateral Shift** | Lateral movement of hip midpoint | Body leans into the turn. |
| **Arm Swing Asymmetry** | Difference in left/right arm swing amplitude | Reduced swing on the turning side. |

Each feature outputs a `rotation_likelihood` (0-1) and a `side` (left/right/none), which are then fused.

---

## Calibration & Adaptation

- **Automatic adaptation**: Every feature has an Exponential Moving Average (EMA) of its raw value. The bias (EMA) continuously drifts toward the current steady-state, so if the person changes their neutral stance (e.g., turns 90 degrees and stays there), the system will treat that new orientation as "straight" after a few seconds.
- **Manual calibration**: Pressing the button overwrites the EMA with the mean of 2 seconds of raw values, instantly re-zeroing all features.

---

## Recording & Logging

- **CSV log**: When `save_history: true`, every frame's feature values (raw and likelihood) are written to `recordings/features_<timestamp>.csv`.
- **Video recording**: When `record_screen: true`, the entire dashboard window is captured as `recordings/dashboard_<timestamp>.mp4`.  
  Both options can be toggled in `config.yaml`.

---

## License

This project is provided for research and development purposes. Feel free to use and modify it.
