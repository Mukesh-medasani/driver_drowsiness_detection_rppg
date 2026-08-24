import cv2
import numpy as np
import time
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from pathlib import Path
from utils.ear import eye_aspect_ratio

# MediaPipe Face Mesh landmark indices for EAR (6 points each)
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]

MODEL_PATH = str(Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task")

class PerceptionAgent:
    def __init__(self):
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

    def process(self, frame):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.time() * 1000)
        detection_result = self.detector.detect_for_video(mp_image, timestamp_ms)
        results = []

        if not detection_result.face_landmarks:
            return results

        for face_landmarks in detection_result.face_landmarks:
            def get_point(idx):
                lm = face_landmarks[idx]
                return np.array([lm.x * w, lm.y * h])

            leftEye  = np.array([get_point(i) for i in LEFT_EYE])
            rightEye = np.array([get_point(i) for i in RIGHT_EYE])
            ear = (eye_aspect_ratio(leftEye) + eye_aspect_ratio(rightEye)) / 2.0

            # Bounding box from all landmarks
            xs = [int(lm.x * w) for lm in face_landmarks]
            ys = [int(lm.y * h) for lm in face_landmarks]
            x,  y  = max(min(xs), 0), max(min(ys), 0)
            x2, y2 = min(max(xs), w), min(max(ys), h)
            bw, bh = x2 - x, y2 - y

            roi = frame[y:y2, x:x2]
            results.append({
                "ear":  ear,
                "roi":  roi,
                "bbox": (x, y, bw, bh)
            })

        return results
