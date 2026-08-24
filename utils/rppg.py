import numpy as np
from scipy.signal import butter, filtfilt, welch
from scipy.fft import rfft, rfftfreq
import statsmodels.api as sm

def sample_roi_center(roi, sample_size=30):
    """
    Sample the center region of ROI for more stable heart rate.
    Avoids edges where skin detection may be unreliable.
    """
    h, w = roi.shape[:2]
    
    # Use central 60% of ROI to avoid face borders
    crop_h = h // 5
    crop_w = w // 5
    roi_center = roi[crop_h:h-crop_h, crop_w:w-crop_w]
    
    if roi_center.size == 0:
        return np.mean(roi[:, :, 1])
    
    # Return green channel mean (better for rPPG)
    return np.mean(roi_center[:, :, 1])

def bandpass(signal, fs=20):
    """
    Bandpass filter for heart rate signal (0.7-4 Hz = 42-240 BPM).
    ML-based approach: Improved signal conditioning before frequency analysis.
    """
    signal = np.asarray(signal, dtype=np.float32)
    if len(signal) < 30:
        return signal
    
    # Detrending: Remove low-frequency drift (DC and very slow changes)
    signal = signal - np.mean(signal)
    if len(signal) > 50:
        signal = signal - np.polyfit(np.arange(len(signal)), signal, 1)[1]
    
    # Nyquist frequency
    nyq = 0.5 * fs
    low_freq = 0.7 / nyq
    high_freq = 4.0 / nyq
    
    # Clamp frequencies
    if low_freq >= 1.0 or high_freq >= 1.0:
        return signal
    
    try:
        # Lower order filter for real-time stability (ML approach uses 2-3)
        b, a = butter(2, [low_freq, high_freq], btype='band')
        filtered = filtfilt(b, a, signal)
        return filtered
    except Exception:
        return signal

def compute_hr_fft(signal, fs=20):
    """
    Compute HR using FFT (Fast Fourier Transform).
    """
    signal = np.asarray(signal, dtype=np.float32)
    if len(signal) < 50:
        return 0
    
    signal = signal - np.mean(signal)
    fft = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), d=1.0 / fs)
    
    valid_mask = (freqs >= 0.7) & (freqs <= 4.0)
    if not np.any(valid_mask):
        return 0
    
    valid_fft = np.abs(fft[valid_mask])
    valid_freqs = freqs[valid_mask]
    
    if valid_fft.size == 0:
        return 0
    
    peak_idx = np.argmax(valid_fft)
    peak_freq = valid_freqs[peak_idx]
    hr = int(round(peak_freq * 60))
    return max(0, min(hr, 200))

def compute_hr_acorr(signal, fs=20):
    """
    Compute HR using Autocorrelation (ML paper method).
    More robust to motion artifacts.
    """
    signal = np.asarray(signal, dtype=np.float32)
    if len(signal) < 50:
        return 0
    
    signal = signal - np.mean(signal)
    
    try:
        # Compute autocorrelation
        acorr = sm.tsa.acf(signal, nlags=len(signal) - 1, fft=True)
        fft = np.fft.rfft(acorr)
        freqs = np.fft.rfftfreq(len(acorr), d=1.0 / fs)
        
        valid_mask = (freqs >= 0.7) & (freqs <= 4.0)
        if not np.any(valid_mask):
            return 0
        
        valid_fft = np.abs(fft[valid_mask])
        valid_freqs = freqs[valid_mask]
        
        if valid_fft.size == 0:
            return 0
        
        peak_idx = np.argmax(valid_fft)
        peak_freq = valid_freqs[peak_idx]
        hr = int(round(peak_freq * 60))
        return max(0, min(hr, 200))
    except Exception:
        return 0

def compute_hr_welch(signal, fs=20):
    """
    Compute HR using Welch's method (ML paper recommends this for stability).
    Best for noisy signals and real-time applications.
    """
    signal = np.asarray(signal, dtype=np.float32)
    if len(signal) < 50:
        return 0
    
    signal = signal - np.mean(signal)
    
    try:
        # Welch's method for power spectral density
        n = len(signal)
        if n < 256:
            seglength = n
            overlap = int(0.8 * n)
        else:
            seglength = 256
            overlap = 200
        
        freqs, power = welch(signal, fs=fs, nperseg=seglength, noverlap=overlap, nfft=2048)
        
        # Extract HR band (0.65 - 4.0 Hz)
        valid_mask = (freqs >= 0.65) & (freqs <= 4.0)
        if not np.any(valid_mask):
            return 0
        
        valid_freqs = freqs[valid_mask]
        valid_power = power[valid_mask]
        
        if valid_power.size == 0:
            return 0
        
        peak_idx = np.argmax(valid_power)
        peak_freq = valid_freqs[peak_idx]
        hr = int(round(peak_freq * 60))
        return max(0, min(hr, 200))
    except Exception:
        return 0

def compute_hr(signal, fs=20):
    """
    Ensemble HR computation using three methods (inspired by ML paper).
    Returns the median of three independent HR estimates for robustness.
    """
    signal = np.asarray(signal, dtype=np.float32)
    if len(signal) < 50:
        return 0
    
    # Compute HR using three different methods
    hr_fft = compute_hr_fft(signal, fs)
    hr_acorr = compute_hr_acorr(signal, fs)
    hr_welch = compute_hr_welch(signal, fs)
    
    # Remove zeros and compute median/mean of valid estimates
    estimates = [h for h in [hr_fft, hr_acorr, hr_welch] if h > 0]
    
    if not estimates:
        return 0
    
    # Use median for robustness (handles outliers better)
    hr = int(np.median(estimates))
    return max(0, min(hr, 200))
