from abc import ABC, abstractmethod

class BasePoseExtractor(ABC):
    @abstractmethod
    def __init__(self, config: dict):
        """config: dictionary with model_path and other options"""
        pass

    @abstractmethod
    def extract(self, frame) -> tuple:
        """
        Takes an RGB frame (numpy array) and returns:
            image_landmarks: dict {name: [px, py]}
            world_landmarks: dict {name: [x, y, z]}   (body‑centric 3D coords)
            visibility:      dict {name: float 0‑1}
        If world landmarks are unavailable (e.g., YOLO), return an empty dict.
        """
        pass