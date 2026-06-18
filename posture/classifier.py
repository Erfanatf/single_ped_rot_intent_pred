import numpy as np
import time

class PostureClassifier:
    def __init__(self, update_interval=0.5):
        self.update_interval = update_interval
        self.last_update = 0
        self.current_posture = "unknown"

    def classify(self, image_landmarks, visibility):
        now = time.time()
        if now - self.last_update < self.update_interval:
            return self.current_posture
        self.last_update = now

        ls = image_landmarks.get('left_shoulder')
        rs = image_landmarks.get('right_shoulder')
        nose = image_landmarks.get('nose')
        if not ls or not rs or not nose:
            return self.current_posture

        # Shoulder width in image
        shoulder_width = abs(ls[0] - rs[0])
        # Shoulder midpoint
        mid_x = (ls[0] + rs[0]) / 2.0

        # Nose offset from shoulder midpoint
        nose_offset = nose[0] - mid_x

        # Heuristic based on shoulder width and nose offset
        # Front/back: shoulders widely separated, nose near center
        if shoulder_width > 100 and abs(nose_offset) < 30:
            # Determine front vs back by which shoulder is left/right in image?
            # Normally when facing camera, right shoulder appears on left (smaller x), left on right.
            if ls[0] > rs[0]:
                self.current_posture = "facing_camera"
            else:
                self.current_posture = "back_to_camera"
        # Side view: shoulders are close together
        elif shoulder_width < 80:
            if nose_offset > 0:
                self.current_posture = "right_side"   # nose right of shoulders → looking to our right, their left side visible
            elif nose_offset < 0:
                self.current_posture = "left_side"
            else:
                self.current_posture = "side_unknown"
        else:
            # Tilted / intermediate
            self.current_posture = "tilted"

        return self.current_posture