import numpy as np
import time
from utils.rppg import bandpass, compute_hr, sample_roi_center
from config import BUFFER_SIZE, CAP_FPS

class HealthAgent:
    """
    Heart rate monitoring via rPPG (remote Photoplethysmography).
    Uses ML-inspired ensemble approach with Welch + FFT + Autocorrelation methods.
    
    Based on: "A Machine Learning–Based Approach for Constructing Remote 
    Photoplethysmogram Signals from Video Cameras" by Castellano et al.
    
    Features:
    - Center-weighted ROI sampling for stability
    - Multi-method HR ensemble (FFT, Welch, Autocorrelation)
    - Median fusion for robustness
    """
    def __init__(self):
        self.signal_buffer = []
        self.time_buffer = []
        self.sample_rate = CAP_FPS
        self.hr = 0
        self.last_hr_time = 0

    def update(self, roi):
        """
        Process ROI and return estimated heart rate (BPM).
        Uses green channel PPG signal with ensemble HR methods.
        """
        current_time = time.time()
        
        if roi is not None and roi.size > 0:
            # Sample center region for stability (avoids face borders)
            green_val = sample_roi_center(roi)
            self.signal_buffer.append(float(green_val))
            self.time_buffer.append(current_time)

        # Keep buffer size bounded
        if len(self.signal_buffer) > BUFFER_SIZE:
            self.signal_buffer.pop(0)
            self.time_buffer.pop(0)

        # Only compute HR when buffer is reasonably filled and 2 seconds have passed
        if len(self.signal_buffer) >= 50 and time.time() - self.last_hr_time >= 2:
            # Compute actual processing framerate to scale frequency correctly
            duration = self.time_buffer[-1] - self.time_buffer[0]
            if duration > 0:
                actual_fs = len(self.time_buffer) / duration
            else:
                actual_fs = self.sample_rate
                
            # Apply bandpass filtering
            filtered = bandpass(self.signal_buffer, actual_fs)
            # Compute HR using ensemble of three methods
            self.hr = compute_hr(filtered, actual_fs)
            self.last_hr_time = time.time()

        return self.hr
