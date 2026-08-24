import cv2

def find_camera():
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Camera found at index {i}")
                cap.release()
                return i
            cap.release()
    return None

idx = find_camera()
if idx is not None:
    print(f"SUCCESS_INDEX_{idx}")
else:
    print("NO_CAMERA_FOUND")
