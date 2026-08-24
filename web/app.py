from flask import Flask, render_template, Response, jsonify
import cv2
import numpy as np
import time
from config import JPEG_QUALITY

app = Flask(__name__)

# Shared data
data = {
    "state": "NORMAL",
    "hr": 0,
    "ear": 0.0
}

# Shared frame
output_frame = None

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data")
def get_data():
    return jsonify(data)


@app.route("/video")
def video():
    print("[DEBUG] /video route called, starting stream generator")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# -----------------------------
# FRAME STREAMING
# -----------------------------

def generate_frames():
    global output_frame

    placeholder_frame = None
    frame_count = 0
    while True:
        frame_to_send = output_frame
        frame_count += 1

        if frame_to_send is None:
            if placeholder_frame is None:
                placeholder_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder_frame, "Waiting for camera...", (25, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            frame_to_send = placeholder_frame

        try:
            ret, buffer = cv2.imencode('.jpg', frame_to_send, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ret:
                if frame_count % 30 == 0:
                    print("[WARN] cv2.imencode failed at frame", frame_count)
                time.sleep(0.01)
                continue
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            if frame_count % 30 == 0:
                print(f"[DEBUG] Stream yielded {frame_count} frames, current frame {len(frame)} bytes")

        except Exception as e:
            print(f"[ERROR] generate_frames yielding frame {frame_count}: {e}")
            time.sleep(0.01)
            continue

        # Limit streaming to roughly 30 FPS to reduce CPU overhead
        time.sleep(0.033)


# -----------------------------
# UPDATE FUNCTION
# -----------------------------

def update(new_state, hr, ear=0.0):
    data["state"] = new_state
    data["hr"] = int(hr)
    data["ear"] = round(float(ear), 4)