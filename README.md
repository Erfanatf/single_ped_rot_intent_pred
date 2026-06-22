````markdown
# Single Pedestrian Rotation Intent Predictor

Real‑time detection of a pedestrian’s **rotation intention** (standing straight, turning left, or turning right) from a single RGB camera.  
The system extracts full‑body keypoints, computes 10 biomechanical features, filters them, fuses the results with a weighted probabilistic engine, and displays everything on a live dashboard with a compass and interactive controls.  
It also computes **rotational kinematics** (angular velocity and acceleration) from the fused intent and can send them to an external robot simulator via UDP, while simultaneously showing a live bird’s‑eye view of the simulation state.

**📖 Navigate through this guide:**  
[Overview](#overview) · [Architecture](#architecture) · [Directory Structure](#directory-structure) · [Installation](#installation) · [Usage](#usage) · [Configuration](#configuration) · [Dashboard & UI](#dashboard--ui) · [Biomechanical Features](#biomechanical-features) · [Calibration & Adaptation](#calibration--adaptation) · [Fusion Engine](#fusion-engine) · [Rotational Kinematics](#rotational-kinematics) · [Recording & Logging](#recording--logging) · [Connectivity](#connectivity) · [Robot Simulator Integration](#robot-simulator-integration) · [Tuning Guidelines](#tuning-guidelines) · [Troubleshooting](#troubleshooting) · [References](#references)

---

## Overview

This project provides a complete pipeline to anticipate a pedestrian’s turn **before it visibly happens** by combining multiple biomechanical cues. It is designed for:

- **Robotics & social navigation** – feed the rotation intent into a mobile robot’s planner.
- **Human‑computer interaction** – trigger actions when a person turns to face a different display.
- **Behavioural research** – record and analyse natural turning behaviour with synchronised video and feature logs.

The system is self‑calibrating, handles different camera viewpoints, and runs in real time on a standard laptop.  
**New in this version** – a bi‑directional integration with an external robot crowd simulator: the predicted angular velocity is sent to the simulator for improved user trajectory prediction, and the simulator’s state is displayed live in a dedicated bird’s‑eye view next to the camera feed.

---

## Architecture

```mermaid
graph TD
    A[Camera / Video / Network] --> B[ThreadedDetector]
    B --> C[Keypoint Filter - optional]
    C --> D[10 Feature Extractors]
    D --> E[Rolling Buffer - 4s]
    E --> F[Intent Fusion]
    F --> G[Dashboard]
    G --> H[Compass]
    G --> I[Plots]
    G --> J[Gait / Posture]
    F --> K[CSV Logger]
    G --> L[Screen Recorder]
    F --> M[Kinematics]
    M --> N[Omega UDP Sender]
    N -.-> O[Robot Simulator]
    O -.-> P[Sim Listener]
    P --> Q[Sim Live View]
    Q --> G
```
````

All heavy processing (pose extraction, feature computation, fusion) runs in a **background thread**, so the UI stays fluid. The kinematics module derives angular velocity and acceleration from the fused net score, and an optional UDP sender broadcasts the angular velocity to an external robot simulator. The simulator sends back the current scene state, which is rendered in a separate live view panel.

**Key components (click to jump):**

- [Pose extraction](#installation) – MediaPipe (default) or YOLO
- [Features](#biomechanical-features) – 10 biomechanical signals
- [Fusion](#fusion-engine) – weighted probabilistic voter
- [Kinematics](#rotational-kinematics) – angular velocity & acceleration
- [Dashboard](#dashboard--ui) – real‑time visualisation
- [Simulator Integration](#robot-simulator-integration) – live sim view and ω feed

---

## Directory Structure

```
single_ped_rot_intent_pred/
├── main.py                     # entry point
├── config.yaml                 # all tunable parameters
├── README.md                   # this document
├── requirements.txt
├── .gitignore
├── extractors/
│   ├── base.py
│   ├── mediapipe_full.py       # MediaPipe 33‑point extractor
│   └── yolo_full.py            # YOLOv8‑pose extractor
├── utils/
│   ├── threaded_detector.py    # background pose thread
│   ├── ukf.py                  # 1D Unscented Kalman Filter
│   ├── kalman.py               # keypoint‑level Kalman filter bank
│   ├── mjpeg_reader.py         # custom MJPEG network stream reader
│   ├── kinematics.py           # rotational velocity & acceleration estimator
│   ├── omega_sender.py         # UDP sender for angular velocity ω
│   └── sim_listener.py         # UDP listener for simulator state
├── features/                   # 10 biomechanical feature classes
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
│   └── intent_fusion.py        # weighted fusion + debounce
├── buffer/
│   └── rolling_buffer.py
├── gait/
│   └── phase_detector.py
├── posture/
│   └── classifier.py
├── ui/
│   ├── dashboard.py
│   ├── camera_widget.py
│   ├── plot_widget.py
│   ├── compass_widget.py
│   ├── gait_widget.py
│   ├── posture_widget.py
│   ├── weight_tuning_widget.py
│   └── sim_view_widget.py      # live simulation bird’s‑eye view
└── recording/
    ├── logger.py
    └── screen_recorder.py
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

The repository includes the required models:

- `pose_landmarker.task` (MediaPipe, either option: lite, full, heavy. For the best accuracy heavy is recommended preserving real-time performance in detection)
- `yolov8n-pose.pt` (YOLO)

If you prefer to download them manually:

- MediaPipe: [Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- YOLO: `yolov8n-pose.pt` is automatically downloaded by Ultralytics on first use.

---

## Usage

All examples assume you are in the project directory and the virtual environment is active.

### Local webcam (default)

```bash
python main.py --model mediapipe
# or specify camera index
python main.py --model mediapipe --source 0
```

### Pre‑recorded video file

```bash
python main.py --model mediapipe --source /path/to/walk_left.mp4
```

### Network stream (e.g., iPhone running IP Camera Lite)

```bash
# With credentials
python main.py --model mediapipe --source http://192.168.1.5:8080/video --user admin --password admin
# Without credentials
python main.py --model mediapipe --source http://192.168.1.5:8080/video
```

### RTSP / RTMP camera

```bash
python main.py --model mediapipe --source rtsp://username:password@192.168.1.10:554/stream1
```

### Custom configuration file

```bash
python main.py --config my_experiment.yaml --model mediapipe
```

### Exit

Simply close the dashboard window. **Do not** use keyboard interrupt (`Ctrl+C`), as this may prevent the screen recorder from saving the video file correctly.

---

## Configuration

All tunable parameters are in `config.yaml`. Below are the most important ones, including the newly added integration options.

| Parameter                    | Default       | Description                                                                                          |
| ---------------------------- | ------------- | ---------------------------------------------------------------------------------------------------- |
| `camera_id`                  | 0             | Camera index (used when `--source` not given)                                                        |
| `frame_width`                | 640           | Capture width (local camera)                                                                         |
| `frame_height`               | 480           | Capture height (local camera)                                                                        |
| `display_downscale`          | 1.0           | Additional scaling for the UI window                                                                 |
| `inference_width`            | 320           | Pose model input width (smaller = faster)                                                            |
| `inference_height`           | 256           | Pose model input height                                                                              |
| `model`                      | mediapipe     | `mediapipe` or `yolo` (overridden by CLI)                                                            |
| `buffer_duration`            | 4.0           | Seconds of feature history shown in plots                                                            |
| `keypoint_filter`            | false         | Enable per‑landmark Kalman smoothing                                                                 |
| `save_history`               | true          | Log features to CSV                                                                                  |
| `record_screen`              | false         | Record dashboard as video                                                                            |
| `output_dir`                 | ./recordings  | Where logs and videos are saved                                                                      |
| `fusion_weights`             | (per‑feature) | Weight of each feature in the fusion engine                                                          |
| `foot_progression_threshold` | 0.15          | Fixed dead‑zone for foot progression difference (radians)                                            |
| `kinematic_scale`            | 2.0           | Rad/s per unit net score derivative – converts fused intent change rate to physical angular velocity |
| `send_omega`                 | false         | If true, broadcasts the angular velocity ω via UDP to `omega_udp_host:omega_udp_port`                |
| `omega_udp_host`             | 127.0.0.1     | Target address for the omega sender                                                                  |
| `omega_udp_port`             | 9999          | Target port for the omega sender                                                                     |

**🔗 Jump to:** [Fusion weights](#fusion-engine) · [Kinematics](#rotational-kinematics) · [Simulator Integration](#robot-simulator-integration)

---

## Dashboard & UI

The dashboard is built with **PySide6** and **pyqtgraph**, using a dark theme.

### Layout

```
┌─────────────┬──────────────────────────────────────────┐
│  Compass    │                                          │
│  (rotation  │        Live Camera View                  │
│   intent)   │        + Skeleton                        │
│             ├──────────────────────────────────────────┤
│  Weight     │        Simulation Live View              │
│  Sliders    │        (bird’s‑eye plot)                 │
├─────────────┴──────────────────────────────────────────┤
│  Gait Phase (L/R)         Body Posture                 │
└───────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│            Feature Plots (2 columns)                     │
│            Likelihood + Raw Value                        │
└──────────────────────────────────────────────────────────┘
```

The central area is now split vertically: the **camera feed with skeleton** occupies the top half, and the **simulation live view** (a top‑down plot of the robot simulator state) the bottom half. Both views are always visible; no tab switching is required. The feature plots are arranged in **2 columns** on the right, giving each subplot more horizontal space.

### What each panel shows

| Panel                    | Content                                                                                                                                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Compass**              | Continuous rotation direction (needle) and discrete intent with confidence. Also shows current angular velocity ω (rad/s) and angular acceleration α (rad/s²).                                                                             |
| **Weight Sliders**       | Sliders 0‑100 for each feature; weight is value/20 (0‑5). Changes take effect immediately.                                                                                                                                                 |
| **Camera View**          | Video stream with full‑body skeleton overlay (33 or 17 points). FPS shown top‑left.                                                                                                                                                        |
| **Simulation Live View** | Bird’s‑eye plot of the robot simulator (when running). Shows user position/facing (green), robot (cyan), goal (yellow), predicted arcs, user path, and nearby pedestrians. Speed readouts for user and robot are displayed below the plot. |
| **Feature Plots**        | One subplot per feature plus angular velocity and acceleration. Left Y‑axis = likelihood (cyan), Right Y‑axis = raw value (orange). X‑axis = last 4 seconds. Auto‑scaling.                                                                 |
| **Gait Phase**           | Stance (green) or Swing (orange) for left and right legs.                                                                                                                                                                                  |
| **Posture**              | Heuristic classification: _Facing Camera_, _Back to Camera_, _Left Side_, _Right Side_, _Tilted_.                                                                                                                                          |

### Controls

- **🔄 Calibrate Neutral** – Stand still in a neutral pose and click. After 2 s the biases of all features are reset. The button changes to “✅ Calibrated”.
- **Weight Sliders** – Drag to adjust the influence of each feature on the final prediction.
- **↺ Reset Views** (above plots) – Restores default zoom ranges (0–4 s, likelihood 0–1).
- The simulation view automatically follows the user (centered). No manual control needed.

---

## Biomechanical Features

All features are computed from MediaPipe’s **world landmarks** (body‑centric frame: **X** = subject’s right, **Y** = up, **Z** = forward, out of the chest). The corrected world coordinate system was empirically verified.

### Yaw angle convention

For a forward‑pointing vector (e.g., foot):  
`yaw = arctan2(vx, -vz)`

For a right‑pointing vector (e.g., shoulder line):  
`yaw = arctan2(-vz, vx)`

**Positive yaw → left turn, negative yaw → right turn.**

#### From landmark to feature – example flow

```mermaid
flowchart LR
    A[World Landmarks] --> B[Segment Vector<br/>v = 'dx, dz']
    B --> C[Yaw Angle<br/>θ = arctan2]
    C --> D[UKF Smoothing]
    D --> E[EMA Bias Correction]
    E --> F[Corrected Value]
    F --> G[Likelihood + Side]
```

### Feature overview table

| Feature                           | Landmarks                   | What it measures                             | Rotation indicator                                          | Threshold |
| --------------------------------- | --------------------------- | -------------------------------------------- | ----------------------------------------------------------- | --------- |
| **Torso‑Pelvis Torsion**          | L/R shoulder, L/R hip       | Angle between shoulder and hip lines         | Positive = left turn, negative = right. Earliest predictor. | 0.15 rad  |
| **Foot Progression Diff.**        | Heels, foot indices, ankles | Yaw difference between front and back foot   | Front foot points toward intended direction.                | 0.15 rad  |
| **Step Width Asymmetry**          | L/R ankle                   | Lateral distance deviation from neutral      | Wider base often precedes a turn (non‑directional).         | 0.08 m    |
| **Shoulder Yaw**                  | L/R shoulder                | Shoulder line orientation vs baseline        | Early upper‑body shift.                                     | 0.15 rad  |
| **Pelvis Yaw**                    | L/R hip                     | Hip line orientation vs baseline             | Confirms trunk rotation.                                    | 0.15 rad  |
| **Head Yaw**                      | L/R ear                     | Interaural axis orientation                  | Head turns before body, but can be overridden.              | 0.25 rad  |
| **CoM Lateral Shift**             | L/R hip                     | Lateral movement of hip midpoint             | Body leans toward turn direction.                           | 0.04 m    |
| **Arm Swing Asymmetry**           | Shoulders, elbows           | Difference in left/right arm swing amplitude | Reduced swing on turning side.                              | 0.15 rad  |
| **Hip Rotation** (disabled)       | Hip, knee                   | Thigh yaw                                    | Internal hip rotation; noisy in practice.                   | 0.20 rad  |
| **Swing Foot Orient.** (disabled) | Heel, foot index, ankle     | Foot yaw during swing                        | Pre‑rotation of swinging foot; swing detection unreliable.  | 0.15 rad  |

Each feature returns a dictionary:

- `value`: bias‑corrected measurement (radians or metres)
- `rotation_likelihood`: 0‑1, how strongly a rotation is detected
- `side`: `'left'`, `'right'`, or `'none'`
- `confidence`: minimum visibility of involved landmarks
- `raw_value`: raw measurement before bias correction (used for calibration)

**Likelihood mapping:**  
If `|c| < threshold`, likelihood = 0; otherwise likelihood = `min(1, (|c| - threshold) / (k * threshold))`.  
Default `k = 1`. The likelihood is then multiplied by the confidence.

---

## Calibration & Adaptation

### Automatic bias correction

Each feature maintains an **Exponential Moving Average (EMA)** of its raw value (or sin/cos for angular features). The EMA acts as a continuously updated neutral reference.  
The corrected value is `c = raw_value - bias`.

**Gated update logic:**  
The EMA is only adjusted when the feature itself signals `'none'` (no rotation), so a long turn won’t drag the neutral reference.

```mermaid
flowchart TD
    A[New raw value] --> B[Apply current bias<br/>→ corrected value]
    B --> C[Classify rotation<br/>side & likelihood]
    C --> D{Side == 'none'?}
    D -->|Yes| E[Update EMA with raw value]
    D -->|No| F[Freeze EMA]
    E --> G[Store corrected output]
    F --> G
```

### Manual calibration

Press the **🔄 Calibrate Neutral** button. The system collects 2 seconds of raw values while you stand still, computes the mean (circular mean for angles), and overwrites the EMA with that value. All features are instantly zeroed.

---

## Fusion Engine

The fusion module combines the 10 individual feature signals into a single **continuous net score** and a **discrete intent label**.

```mermaid
flowchart LR
    subgraph Features
        F1[Feature 1<br/>ℓ1, s1]
        F2[Feature 2<br/>ℓ2, s2]
        F3[...]
        FN[Feature N<br/>ℓN, sN]
    end
    F1 --> WL[Weighted Left Sum<br/>L = Σ w_i ℓ_i for s_i='left']
    F2 --> WL
    FN --> WL
    F1 --> WR[Weighted Right Sum<br/>R = Σ w_i ℓ_i for s_i='right']
    F2 --> WR
    FN --> WR
    WL --> Norm[Divide by total weight W]
    WR --> Norm
    Norm --> Net[S_net = L̄ - R̄]
    Net --> EMA[EMA Smoothing]
    EMA --> DB{Debounce & Hysteresis}
    DB --> Intent[Discrete Intent<br/>Straight / Rotate Left / Rotate Right]
    DB --> Score[Continuous Net Score<br/>-1..1]
```

### Algorithm steps

1. **Weighted vote:**  
   `L = Σ w_i * ℓ_i` for features voting `'left'`  
   `R = Σ w_i * ℓ_i` for features voting `'right'`  
   Default weights: Torso Torsion = 3.0, Foot Diff = 2.5, Shoulder Yaw = 2.0, Pelvis Yaw = 2.0, CoM Shift = 2.0, Head Yaw = 1.5, Arm Swing = 1.0, Step Width = 1.0.

2. **Normalise:**  
   `L̄ = L / W`, `R̄ = R / W`, where `W` is the total weight of voting features.

3. **Net score:**  
   `S_net = L̄ - R̄` (range [-1, 1], positive = left).

4. **Smoothing:** EMA applied to `L̄` and `R̄` (α = 0.2).

5. **Debounce:**  
   Dead zone ±0.05 → `'Straight'`.  
   Requires 5 consecutive frames of the same raw intent to switch state.

### Output

- Discrete intent: `'Straight'`, `'Rotate Left'`, `'Rotate Right'`
- Confidence: `min(1, 3 * |S_net|)`
- Continuous net score (displayed by the compass needle)

**Live weight tuning:** Sliders on the left dock instantly update the weights dictionary.

---

## Rotational Kinematics

A new module (`utils/kinematics.py`) derives the **angular velocity** ω (rad/s) and **angular acceleration** α (rad/s²) from the fused continuous net score $S_{\text{net}}$. The algorithm uses a finite‑difference slope between consecutive $S_{\text{net}}$ values, followed by an exponential moving average (EMA) for smoothing.

**Update rule:**  
Let $s_t$ be the net score at time $t$, and $\Delta t$ the time since the last update. The raw velocity is:
$$v_{\text{raw}} = s_t$$
The smoothed velocity is:
$$v_{\text{ema}} = \alpha \cdot v_{\text{raw}} + (1 - \alpha) \cdot v_{\text{ema}}$$
with $\alpha = 0.2$. Angular acceleration is then obtained as:
$$a = \frac{v_{\text{ema}} - v_{\text{prev}}}{\Delta t}$$
Finally, a configurable **scale factor** (`kinematic_scale`, default 2.0) converts the unitless derivative to physical radians per second:
$$\omega = \text{scale} \cdot v_{\text{ema}}, \qquad a_{\text{phys}} = \text{scale} \cdot a$$

**Gating:** The kinematics update is **only performed when the discrete fusion intent is not `'Straight'`** (i.e., the person is actively rotating). When the intent returns to straight, the kinematics state is reset. This prevents the gradual bias adaptation from generating a false reverse angular velocity.

The resulting ω and α are shown on the compass widget, logged to CSV, and optionally sent to an external robot simulator via UDP.

---

## Recording & Logging

Set `save_history: true` and/or `record_screen: true` in `config.yaml`.

### CSV feature log

- File: `recordings/features_<timestamp>.csv`
- One row per processed frame.
- Columns: `timestamp`, plus for each feature: `{name}_value`, `{name}_rotation_likelihood`, `{name}_confidence`.  
  Additionally, `angular_velocity` and `angular_acceleration` are logged as separate columns when kinematics are active.
- Safe for sudden termination (flushed every write).

### Dashboard screen recording

- File: `recordings/dashboard_<timestamp>.mp4` (or `.avi` fallback).
- Captures the full dashboard window, including plots, compass, and simulation view.
- Robust codec selection: tries `mp4v`, `avc1`, `X264`, `XVID`, `MJPG` until one works.

---

## Connectivity

The `--source` argument accepts:

| Source type  | Example                                  | Notes                                                                     |
| ------------ | ---------------------------------------- | ------------------------------------------------------------------------- |
| Local webcam | `--source 0`                             | Integer index; resolution set from config.                                |
| Video file   | `--source walk.mp4`                      | Any format OpenCV can read.                                               |
| HTTP MJPEG   | `--source http://192.168.1.5:8080/video` | Custom reader (bypasses FFmpeg). Add `--user` and `--password` if needed. |
| RTSP/RTMP    | `--source rtsp://...`                    | Handled by OpenCV’s FFmpeg.                                               |

```mermaid
flowchart TD
    A[--source argument] --> B{Is it a digit?}
    B -->|Yes| C[Local Webcam<br/>cv2.VideoCapture - index]
    B -->|No| D{Starts with http/rtsp?}
    D -->|Yes| E[Network Stream]
    D -->|No| F[Video File]
    E --> G{HTTP MJPEG?}
    G -->|Yes| H[MJPEGReader<br/>proxy bypass, mDNS]
    G -->|No| I[OpenCV FFmpeg<br/>RTSP/RTMP]
```

**Troubleshooting network streams:**

- If you get “Network stream interrupted”, ensure both devices are on the same network.
- Proxy issues are automatically handled (proxy env vars cleared during connection).
- For iPhone apps like IP Camera Lite, use the exact URL shown in the app; force the app to use the hotspot interface if the IP is wrong.

---

## Robot Simulator Integration

The rotation predictor can be linked with an external robot crowd simulator (the `robot_demo.py` example) to provide **real‑time angular velocity** for improved user trajectory prediction, and to **visualise the simulation state** live inside the dashboard.

### Sending angular velocity (ω) to the simulator

- Module: `utils/omega_sender.py`
- Activated by setting `send_omega: true` in `config.yaml`.
- A background thread periodically sends the current ω (in rad/s) as a plain‑text string via UDP to `127.0.0.1:9999` (configurable).
- The simulator receives this value and, when non‑zero, uses a **unicycle model** (constant speed, constant turn rate) to predict the user’s future path over a 2‑second lookahead, replacing the default constant‑velocity straight line.

### Receiving simulator state for live view

- Module: `utils/sim_listener.py`
- Listens on UDP port `9998` for JSON‑formatted state packets sent by the simulator.
- The state includes user position/facing, robot position/heading, goal point, predicted arcs, nearby pedestrians, and speed values.
- The `ui/sim_view_widget.py` widget renders this data as a bird’s‑eye plot with a legend, speed readouts, and auto‑centering on the user.

### Running the integrated system

1. Start the rotation predictor with `send_omega: true` and (optionally) a live camera feed.
2. Launch the robot simulator (e.g., `python -m src.sfm_navigation.demo.robot_demo --controller SFM`). The simulator automatically listens for ω on port 9999 and sends its state to port 9998.
3. The dashboard will display the simulation live view in the bottom half of the central area.
4. The simulator runs in real‑time (synchronised to wall clock) so that the external ω aligns correctly with the simulation timeline.

The integration is non‑invasive: if the predictor is not running, the simulator falls back to its original constant‑velocity prediction; if the simulator is not running, the predictor simply does not receive state data and the live view remains inactive.

---

## Tuning Guidelines

### Adjusting feature weights

- Start with default weights.
- If the compass is biased toward one side when you walk straight, increase the weight of `torso_pelvis_torsion` (most reliable) or reduce noisy features like `head_yaw`.
- Use the weight sliders during a recording session to quickly find the best balance.

### Adapting the dead zone (threshold)

- `foot_progression_threshold` in config.yaml can be raised if you see false positives when walking straight.
- Individual feature thresholds are hard‑coded (0.15 rad, etc.) but can be changed in the feature’s constructor in `main.py`.

### Keypoint filter

- Enable `keypoint_filter: true` if you notice jitter in the raw plots. It adds a small CPU cost but yields smoother feature signals.

### Kinematic scale

- `kinematic_scale` converts the derivative of the fused net score (unitless) to physical angular velocity (rad/s).
- To tune it: turn at a known constant speed (e.g., 90° in 1 s = ~1.57 rad/s). If the displayed ω is too low, increase the scale; if too high, decrease it. A value of 2.0 is a reasonable starting point.

### Recording performance

- If screen recording causes frame drops, disable `record_screen` or reduce the dashboard window size.
- For pure data collection, keep `save_history: true` and `record_screen: false`.

---

## Troubleshooting

| Symptom                               | Probable cause                                    | Solution                                                                                                                 |
| ------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Dashboard doesn’t start               | Missing packages or model files                   | Ensure `pip install -r requirements.txt` completed and model files exist.                                                |
| Camera feed is black                  | Wrong camera index                                | Try `--source 0`, `1`, etc. or check system camera permissions.                                                          |
| Skeleton not drawn                    | Person not detected or facing away                | Ensure you are visible in the camera; the system draws only when landmarks are available.                                |
| Compass always “Rotate Left”          | Foot yaw formula used incorrectly (older version) | Update feature files to latest corrected formulas.                                                                       |
| “Network stream interrupted”          | Proxy variable interfering or wrong URL           | Check that proxy is cleared (handled automatically) or use direct IP.                                                    |
| “Stream ends prematurely”             | FFmpeg cannot parse MJPEG container               | Use `--source http://...` for MJPEG; the custom reader will be used.                                                     |
| Plots empty or frozen                 | A feature threw an exception                      | Look for “Feature … failed” messages in the terminal; disable that feature temporarily.                                  |
| Recording video unplayable            | Codec not available                               | A fallback codec will be tried; ensure `avc1` or `XVID` codec is installed (usually present).                            |
| Grey/colour lines in stream           | JPEG boundaries not parsed correctly              | Ensure using `MJPEGReader` (default for HTTP). Restart the stream.                                                       |
| Simulation live view shows “Waiting…” | Simulator not sending state / port mismatch       | Check that simulator is running and `send_sim_state` targets `127.0.0.1:9998`. Restart both processes.                   |
| Omega always zero despite turning     | Kinematic scale too low / features not voting     | Increase `kinematic_scale`; check that fusion weights are non‑zero and that features are returning non‑zero likelihoods. |
| False reverse ω after holding a turn  | Kinematics not gated by intent                    | Ensure `kinematics.reset()` is called when intent becomes `'Straight'`. Update to latest `dashboard.py`.                 |

---

## License

This project is provided for research and development. You are free to use, modify, and distribute it.