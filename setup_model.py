"""
setup_model.py — Downloads the MediaPipe FaceLandmarker model and checks dependencies.
Run this ONCE before starting main.py.
"""

import os
import urllib.request

MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL_PATH = "models/face_landmarker.task"

def download_model():
    if os.path.exists(MODEL_PATH):
        print(f"[OK] Model already exists at {MODEL_PATH}")
        return
    os.makedirs("models", exist_ok=True)
    print("Downloading face_landmarker.task (~5MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[OK] Model saved to {MODEL_PATH}")

def check_dependencies():
    print("\nChecking dependencies...")
    missing = []
    deps = ["cv2", "mediapipe", "scipy", "flask", "twilio", "numpy"]
    for dep in deps:
        try:
            __import__(dep)
            print(f"  [OK] {dep}")
        except ImportError:
            print(f"  [MISSING] {dep}")
            missing.append(dep)

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
    else:
        print("\n[OK] All dependencies satisfied. You can now run: python main.py")

if __name__ == "__main__":
    download_model()
    check_dependencies()
