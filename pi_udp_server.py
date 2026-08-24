import socket
import time
import threading
import atexit
import platform
import sys

GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] RPi.GPIO not available: {e}")
    print("[WARN] Running without GPIO support. Motor commands will be printed, and laptop sound will be used for alerts.")

# Configuration
UDP_IP = "0.0.0.0"  # Listen on all interfaces
UDP_PORT = 5005
TIMEOUT_SECONDS = 0.5  # Fail-safe: Stop motors if no data received for 0.5s

# ---------------------------------------------------------
# GPIO PINS (BCM)
# ---------------------------------------------------------
IN1, IN2, IN3, IN4 = 22, 23, 24, 25
ENA, ENB = 12, 18
# ---------------------------------------------------------

if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in [IN1, IN2, IN3, IN4, ENA, ENB]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    pwmA = GPIO.PWM(ENA, 1000)
    pwmB = GPIO.PWM(ENB, 1000)
    pwmA.start(0)
    pwmB.start(0)
else:
    pwmA = None
    pwmB = None

current_state = "STOP"
current_speed = 0
state_lock = threading.Lock()

# -------------------------
# Motor helper functions
# -------------------------

def set_speed(speed):
    global current_speed
    speed = max(0, min(100, speed))
    if GPIO_AVAILABLE:
        pwmA.ChangeDutyCycle(speed)
        pwmB.ChangeDutyCycle(speed)
        print(f"[DEBUG] PWM set to {speed}%")
    else:
        print(f"[MOTOR] set_speed({speed})")
    current_speed = speed


def stop_motors():
    set_speed(0)
    if GPIO_AVAILABLE:
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)
    else:
        print("[MOTOR] stop_motors()")


def move_forward(speed=100):
    if GPIO_AVAILABLE:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)
    else:
        print(f"[MOTOR] move_forward({speed})")
    set_speed(speed)


def slow_forward(speed=40):
    if GPIO_AVAILABLE:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)
    else:
        print(f"[MOTOR] slow_forward({speed})")
    set_speed(speed)


def change_speed(target_speed, step=10, delay=0.05):
    global current_speed
    target_speed = max(0, min(100, target_speed))
    if current_speed == target_speed:
        return

    step = abs(step)
    if current_speed < target_speed:
        ramp = range(current_speed + step, target_speed + 1, step)
    else:
        ramp = range(current_speed - step, target_speed - 1, -step)

    for speed in ramp:
        set_speed(speed)
        time.sleep(delay)


def emergency_brake():
    print("[ACTION] Emergency brake initiated")
    change_speed(0, step=20, delay=0.08)
    stop_motors()


def laptop_beep(duration_ms=100, frequency=1000):
    if sys.platform == "win32":
        try:
            import winsound
            winsound.Beep(frequency, duration_ms)
        except Exception as e:
            print(f"[WARN] winsound failed: {e}")
    else:
        # Terminal bell fallback for Linux/macOS
        print("\a", end="", flush=True)
        time.sleep(duration_ms / 1000.0)


def buzzer_alert(count=4, on_time=0.08, off_time=0.08):
    for _ in range(count):
        laptop_beep(duration_ms=int(on_time * 1000))
        time.sleep(off_time)


def play_alert():
    try:
        buzzer_alert(6, 0.06, 0.06)
    except Exception as e:
        print(f"[WARN] Laptop buzzer alert failed: {e}")

# -------------------------
# UDP server
# -------------------------

print("[STARTING] Initializing GPIO motor controller...")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(0.1)

print(f"[LISTENING] UDP Server listening on port {UDP_PORT}")

last_received_time = time.time()
last_state = None

try:
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            state = data.decode("utf-8").strip()
            last_received_time = time.time()

            if state != last_state:
                print(f"[{addr[0]}] State Changed: {state}")
                last_state = state
                print(f"[DEBUG] current_speed before state action: {current_speed}")

                with state_lock:
                    if state == "NORMAL":
                        print("[ACTION] NORMAL - full speed forward")
                        move_forward(100)
                        print(f"[DEBUG] current_speed after NORMAL: {current_speed}")

                    elif state == "DROWSY":
                        print("[ACTION] DROWSY - slow down and alert")
                        move_forward(25)
                        print(f"[DEBUG] current_speed after DROWSY: {current_speed}")
                        threading.Thread(target=play_alert, daemon=True).start()

                    elif state == "CRITICAL":
                        print("[ACTION] CRITICAL - emergency brake")
                        threading.Thread(target=emergency_brake, daemon=True).start()
                        print(f"[DEBUG] current_speed after CRITICAL: {current_speed}")

                    elif state == "NO_FACE":
                        print("[ACTION] NO_FACE - driver missing, stopping motors")
                        stop_motors()
                        print(f"[DEBUG] current_speed after NO_FACE: {current_speed}")

                    elif state == "STOP":
                        print("[ACTION] STOP - stopping motors")
                        stop_motors()
                        print(f"[DEBUG] current_speed after STOP: {current_speed}")

                    else:
                        print(f"[WARN] Unknown state '{state}', stopping motors")
                        stop_motors()
                        print(f"[DEBUG] current_speed after UNKNOWN: {current_speed}")

                # Update receive time again after processing state to avoid false timeouts
                last_received_time = time.time()

        except socket.timeout:
            pass

        if time.time() - last_received_time > TIMEOUT_SECONDS:
            if last_state != "TIMEOUT":
                print(f"[WARNING] No UDP data received for {TIMEOUT_SECONDS}s! Connection lost. Applying fail-safe stop.")
                last_state = "TIMEOUT"
                stop_motors()

except KeyboardInterrupt:
    print("\n[STOPPING] Shutting down...")
finally:
    stop_motors()
    if pwmA is not None:
        pwmA.stop()
    if pwmB is not None:
        pwmB.stop()
    sock.close()
    if GPIO_AVAILABLE:
        GPIO.cleanup()


def cleanup():
    stop_motors()
    if pwmA is not None:
        pwmA.stop()
    if pwmB is not None:
        pwmB.stop()
    if GPIO_AVAILABLE:
        GPIO.cleanup()

atexit.register(cleanup)
