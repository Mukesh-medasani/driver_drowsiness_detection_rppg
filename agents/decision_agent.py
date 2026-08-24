from config import EAR_THRESHOLD, EAR_CONSEC_FRAMES, HR_LOW, HR_HIGH

class DecisionAgent:
    def __init__(self):
        self.counter = 0

    def decide(self, ear, hr):
        if ear < EAR_THRESHOLD:
            self.counter += 1
        else:
            self.counter = 0

        if self.counter > EAR_CONSEC_FRAMES:
            return "DROWSY"

        elif hr != 0 and (hr < HR_LOW or hr > HR_HIGH):
            return "CRITICAL"

        return "NORMAL"
