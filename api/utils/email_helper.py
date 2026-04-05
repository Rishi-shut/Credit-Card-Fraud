"""
Email alert helper — sends Gmail notifications when fraud is detected.

IMPORTANT: MAIL_PASSWORD must be a Gmail App Password (16 letters only).
How to get one: Google Account → Security → 2-Step Verification → App Passwords → Generate
"""
import os
from flask_mail import Mail, Message

mail = Mail()


def send_fraud_alert(recipient_email: str, fraud_probability: float, amount: float) -> bool:
    """Send a fraud alert email. Returns True if sent successfully."""
    try:
        subject = f"🚨 FraudGuard Alert: Fraud Detected ({fraud_probability*100:.1f}% probability)"
        body = f"""
FraudGuard Fraud Alert
======================

A transaction has been flagged as potentially fraudulent.

Details:
  • Fraud Probability : {fraud_probability*100:.1f}%
  • Transaction Amount: ${amount:.2f}
  • Status            : FRAUD DETECTED

This alert was triggered because the fraud probability exceeded your
configured threshold.

Log in to your FraudGuard dashboard to review the full prediction history.

─────────────────────────────────
FraudGuard — AI-Powered Fraud Detection
This is an automated alert. Do not reply to this email.
        """.strip()

        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[Email Alert] Failed to send: {e}")
        return False


def send_test_email(recipient_email: str) -> bool:
    """Send a test email to verify alert configuration."""
    try:
        msg = Message(
            subject="✅ FraudGuard — Alert Configuration Confirmed",
            recipients=[recipient_email],
            body="Your FraudGuard email alerts are working correctly!\n\nYou will receive alerts when fraud is detected above your configured threshold."
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[Email Test] Failed: {e}")
        return False
