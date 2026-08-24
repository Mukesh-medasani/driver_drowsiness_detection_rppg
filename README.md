# 🚗 Real-Time Driver Drowsiness Detection using rPPG

A real-time driver monitoring system that detects driver drowsiness using facial landmarks, Eye Aspect Ratio (EAR), temporal eye-closure analysis, and remote Photoplethysmography (rPPG). The system also provides real-time alerts and integrates with a Raspberry Pi for hardware-based notifications.

## 📌 Overview

Driver fatigue is a major cause of road accidents. This project provides a real-time monitoring solution that analyzes facial and physiological signals from a webcam to identify potential drowsiness.

The system combines:

- Facial landmark detection using MediaPipe
- Eye Aspect Ratio (EAR)
- Temporal eye-closure analysis
- Remote Photoplethysmography (rPPG)
- Heart-rate estimation
- Rule-based driver-state classification
- Real-time alerts
- Flask-based monitoring dashboard
- Raspberry Pi integration through UDP

## 🏗️ System Architecture

```text
                    Webcam
                       │
                       ▼
                 OpenCV Capture
                       │
                       ▼
              MediaPipe Face Landmarks
                       │
              ┌────────┴─────────┐
              │                  │
              ▼                  ▼
         Eye Landmarks        Face ROI
              │                  │
              ▼                  ▼
        EAR Calculation       rPPG Signal
              │                  │
              │             Green Channel
              │                  │
              │             Bandpass Filter
              │                  │
              │          ┌───────┴────────┐
              │          │                │
              │         FFT             Welch
              │          │                │
              │          └───────┬────────┘
              │                  │
              │            Autocorrelation
              │                  │
              │                  ▼
              │          Heart Rate Estimate
              │                  │
              └──────────┬───────┘
                         ▼
                  Decision Agent
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           NORMAL      DROWSY      CRITICAL
             │           │           │
             └───────────┼───────────┘
                         ▼
                  Alert / Hardware
                    │          │
                    ▼          ▼
             Email / SMS    Raspberry Pi
                         │
                         ▼
                   Flask Dashboard
