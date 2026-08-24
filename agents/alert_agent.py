import time
import smtplib
import winsound
from email.mime.text import MIMEText
from config import (
    EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVERS,
    TWILIO_SID, TWILIO_AUTH, TWILIO_PHONE, EMERGENCY_CONTACTS
)
from twilio.rest import Client

class AlertAgent:
    def __init__(self):
        self.last_alert = 0
        self.client = Client(TWILIO_SID, TWILIO_AUTH)

    def alarm(self):
        winsound.Beep(1000, 300)

    def send_email(self, message):
        try:
            msg = MIMEText(message)
            msg['Subject'] = "[ALERT] Driver Emergency Alert"
            msg['From'] = EMAIL_SENDER
            msg['To'] = ", ".join(EMAIL_RECEIVERS)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            print("[EMAIL] Email sent")

        except Exception as e:
            print("Email error:", e)

    def send_sms(self, message):
        try:
            for number in EMERGENCY_CONTACTS:
                self.client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE,
                    to=number
                )
            print("[SMS] SMS sent")

        except Exception as e:
            print("SMS error:", e)

    def act(self, state, hr):
        if state == "DROWSY":
            self.alarm()
            print("[WARNING] Vehicle: SLOW DOWN")

        elif state == "CRITICAL":
            self.alarm()
            print("[CRITICAL] Vehicle: STOP")

            if time.time() - self.last_alert > 15:
                message = f"""
DRIVER EMERGENCY ALERT

Condition: CRITICAL
Heart Rate: {int(hr)}
Time: {time.ctime()}

Immediate attention required!
"""
                self.send_email(message)
                self.send_sms(message)
                self.last_alert = time.time()

        else:
            print("[OK] Vehicle: NORMAL")
