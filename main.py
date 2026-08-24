import cv2
import numpy as np
import threading
import time
import traceback
from queue import Queue, Empty

from agents.perception_agent import PerceptionAgent
from agents.health_agent import HealthAgent
from agents.decision_agent import DecisionAgent
from agents.alert_agent import AlertAgent
from agents.hardware_agent import HardwareAgent
from config import FRAME_WIDTH, FRAME_HEIGHT, CAP_FPS, BRIGHTNESS_BOOST, CONTRAST, JPEG_QUALITY

from web.app import app, update
import web.app as webapp  # for frame sharing

print("[SYSTEM] Starting Driver Monitoring System...")

# Initialize agents
perception = PerceptionAgent()
health = HealthAgent()
decision = DecisionAgent()
alert = AlertAgent()
hardware = HardwareAgent()

# Start Flask server
def run_flask():
    print("[SYSTEM] Web Dashboard: http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

# -----------------------------
# PC WEBCAM (DEFAULT CAMERA)
# -----------------------------
ENABLE_LOCAL_PREVIEW = False
# FRAME_WIDTH = 640  # Now imported from config
# FRAME_HEIGHT = 480
# CAP_FPS = 20


def open_camera(max_index=3):
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
        if not cap.isOpened():
            cap.release()
            continue

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, CAP_FPS)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"[SUCCESS] Webcam connected on index {idx}.")
        print(f"[INFO] Capture resolution: {actual_width}x{actual_height} @ {actual_fps:.1f} FPS")
        return cap

    return None

cap = open_camera()
if cap is None or not cap.isOpened():
    print("[ERROR] Webcam not accessible on any camera index!")

frame_queue = Queue(maxsize=2)
stop_event = threading.Event()
FRAME_SKIP = 1
frame_count = 0  # For main loop only
capture_check_count = 0  # For capture loop diagnostics
last_bbox = None
last_state = "NORMAL"
last_hr = 0
last_ear = 0.0
last_color = (0, 255, 0)
face_hold = 0
MAX_FACE_HOLD = 30  # Number of frames before triggering NO_FACE fail-safe
default_bbox = (480, 270, 320, 180)  # Center square for continuous display
last_bbox = default_bbox


def enhance_brightness(frame):
    # Completely bypass artificial enhancement to preserve native webcam quality
    return frame


def draw_bbox(frame, bbox, state, hr, color):
    x, y, w, h = bbox
    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
    cv2.putText(frame, f"{state}", (x, y-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(frame, f"HR: {int(hr)}", (x, y+h+20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)


def capture_loop():
    """Thread to continuously capture frames from the webcam and send directly to Flask."""
    frame_check = 0
    while not stop_event.is_set():
        try:
            frame_check += 1
            
            if cap is None or not cap.isOpened():
                time.sleep(0.5)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Removed artificial resize to preserve maximum native crispness

            frame = enhance_brightness(frame)

            # Try to put in queue for main loop processing
            try:
                frame_queue.put(frame, block=False)
            except Exception:
                try:
                    frame_queue.get_nowait()
                    frame_queue.put(frame, block=False)
                except Exception:
                    pass

            # ALSO directly update Flask so streaming never starves
            if frame_check % 2 == 0:  # Send to Flask at ~10 FPS minimum
                out_frame = frame.copy()
                if last_bbox is not None:
                    draw_bbox(out_frame, last_bbox, last_state, last_hr, last_color)
                webapp.output_frame = out_frame
                
            if frame_check % 60 == 0:
                print(f"[DEBUG] Capture: {frame_check} frames, queue size {frame_queue.qsize()}")

        except Exception as e:
            print("[ERROR] capture_loop:", e)
            traceback.print_exc()
            time.sleep(0.5)
        finally:
            time.sleep(0.001)

capture_thread = threading.Thread(target=capture_loop, daemon=True)
capture_thread.start()
print("[DEBUG] Capture thread started")

# Wait a moment before starting main loop to let capture populate frames
time.sleep(0.5)

# -----------------------------
# MAIN LOOP
# -----------------------------
main_loop_count = 0
while not stop_event.is_set():
    try:
        frame = frame_queue.get(timeout=0.1)
    except Empty:
        if main_loop_count % 30 == 0:
            print("[WARN] Main loop: no frame in queue")
        time.sleep(0.002)
        main_loop_count += 1
        continue

    main_loop_count += 1

    frame_count += 1

    if frame_count % FRAME_SKIP != 0:
        if last_bbox is not None:
            draw_bbox(frame, last_bbox, last_state, last_hr, last_color)
        webapp.output_frame = frame.copy()
        continue

    results = perception.process(frame)

    if not results:
        face_hold += 1
        if face_hold > MAX_FACE_HOLD:
            last_bbox = None
            last_state = "NO_FACE"
            
        if last_bbox is not None:
            draw_bbox(frame, last_bbox, last_state, last_hr, last_color)
            webapp.output_frame = frame.copy()
            update(last_state, last_hr, last_ear)
            hardware.act(last_state)
        else:
            webapp.output_frame = frame.copy()
            update("NO_FACE", 0, 0.0)
            hardware.act("NO_FACE")
        continue

    face_hold = 0

    for res in results:
        ear = res["ear"]
        roi = res["roi"]

        hr = health.update(roi)
        state = decision.decide(ear, hr)

        alert.act(state, hr)
        hardware.act(state)
        update(state, hr, ear)

        (x, y, w, h) = res["bbox"]
        last_bbox = (x, y, w, h)
        last_state = state
        last_hr = hr
        last_ear = ear
        last_color = (0, 0, 255) if state in ["DROWSY", "CRITICAL"] else (0, 255, 0)

        draw_bbox(frame, last_bbox, last_state, last_hr, last_color)

    # Send frame to Flask
    webapp.output_frame = frame.copy()

    if ENABLE_LOCAL_PREVIEW:
        cv2.imshow("Driver Monitor", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            stop_event.set()
            break

stop_event.set()
capture_thread.join(timeout=1.0)
cap.release()
cv2.destroyAllWindows()