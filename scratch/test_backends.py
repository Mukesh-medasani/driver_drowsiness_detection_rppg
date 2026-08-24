import cv2

def test_camera_backends():
    # List of common Windows backends
    backends = [
        ("Default", None),
        ("DSHOW", cv2.CAP_DSHOW),
        ("MSMF", cv2.CAP_MSMF),
        ("VFW", cv2.CAP_VFW)
    ]
    
    found = False
    for name, backend in backends:
        print(f"--- Testing Backend: {name} ---")
        for i in range(5):
            if backend is not None:
                cap = cv2.VideoCapture(i, backend)
            else:
                cap = cv2.VideoCapture(i)
                
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"SUCCESS: Found camera at index {i} using {name}")
                    found = True
                    cap.release()
                    break
                else:
                    print(f"Index {i}: Opened but could not read frame.")
                cap.release()
            else:
                pass # Not opened
    
    if not found:
        print("RESULT: No camera found on any backends.")

test_camera_backends()
