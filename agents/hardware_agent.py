import socket
import time
from config import RASPBERRY_PI_IP

UDP_PORT = 5005

class HardwareAgent:
    """
    Handles physical hardware actuation by sending UDP datagrams
    to the Raspberry Pi. UDP provides near-zero latency.
    """
    def __init__(self):
        self.last_state = None
        self.pi_address = (RASPBERRY_PI_IP, UDP_PORT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.last_sent_time = 0
        
    def act(self, state):
        """
        Send state to Raspberry Pi via UDP.
        Sends continuously to ensure the Pi always has the latest state,
        even if some packets are dropped over Wi-Fi.
        """
        current_time = time.time()
        
        # Limit sending rate to ~30Hz max to avoid network flooding
        if current_time - self.last_sent_time > 0.03: 
            self.last_state = state
            self.last_sent_time = current_time
            
            try:
                # Send the state as a simple encoded string (fire and forget)
                self.sock.sendto(state.encode('utf-8'), self.pi_address)
            except Exception as e:
                print(f"[HARDWARE ERROR] UDP Send Failed: {e}")
