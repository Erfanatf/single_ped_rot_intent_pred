import cv2
import numpy as np

# Full connections for MediaPipe (33 points), but we'll define a mapping for general use.
# We'll create a list of (start_name, end_name) for bones we want to draw.
# The drawer will draw only if both endpoints are present in the keypoints dict.

FULL_SKELETON_CONNECTIONS = [
    # Face
    ("nose", "left_eye_inner"), ("nose", "right_eye_inner"),
    ("left_eye_inner", "left_eye"), ("left_eye", "left_eye_outer"),
    ("right_eye_inner", "right_eye"), ("right_eye", "right_eye_outer"),
    ("left_eye", "left_ear"), ("right_eye", "right_ear"),
    ("mouth_left", "mouth_right"),
    ("nose", "mouth_left"), ("nose", "mouth_right"),
    # Upper body
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    # Torso
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    # Lower body
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
    # Feet (if available)
    ("left_ankle", "left_heel"), ("left_heel", "left_foot_index"),
    ("right_ankle", "right_heel"), ("right_heel", "right_foot_index"),
    # Hands (fingers) – optional, but we'll include if keypoints exist
    ("left_wrist", "left_thumb"), ("left_wrist", "left_pinky"),
    ("left_wrist", "left_index"),
    ("right_wrist", "right_thumb"), ("right_wrist", "right_pinky"),
    ("right_wrist", "right_index"),
]

# Color scheme: left side = green, right side = red, center = gold
def joint_color(name):
    if "left" in name:
        return (0, 255, 0)    # green
    elif "right" in name:
        return (0, 0, 255)    # red
    else:
        return (0, 215, 255)  # gold

def draw_skeleton(frame, keypoints, draw_face=True, draw_hands=True):
    """
    Draws full skeleton on the frame.
    keypoints: dict {name: [x, y, ...]}
    """
    if not keypoints:
        return

    # Draw bones
    for start, end in FULL_SKELETON_CONNECTIONS:
        # Skip face connections if draw_face is False
        if not draw_face and ("eye" in start or "eye" in end or "ear" in start or "ear" in end or "mouth" in start or "mouth" in end):
            continue
        # Skip hand connections if draw_hands is False
        if not draw_hands and ("thumb" in start or "pinky" in start or "index" in start or "thumb" in end or "pinky" in end or "index" in end):
            continue
        if start in keypoints and end in keypoints:
            pt1 = (int(keypoints[start][0]), int(keypoints[start][1]))
            pt2 = (int(keypoints[end][0]), int(keypoints[end][1]))
            cv2.line(frame, pt1, pt2, (255, 255, 0), 1, cv2.LINE_8)

    # Draw joints
    for name, data in keypoints.items():
        if len(data) < 2:
            continue
        x, y = int(data[0]), int(data[1])
        if x <= 0 and y <= 0:
            continue
        color = joint_color(name)
        cv2.circle(frame, (x, y), 3, color, -1, cv2.LINE_8)