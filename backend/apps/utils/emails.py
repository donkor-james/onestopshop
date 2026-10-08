import secrets
import resend
from backend.config.settings import base

resend.api_key = base.RESEND_API_KEY


def send_verification_code(user):
    otp = ''.join(str(secrets.randbelow(10)) for _ in range(6))

    subject = "OneStopShop Email Verification"
    message = f"""
Hello, {user.first_name}\n
Welcome to OneStopShop!
Your OTP is {otp}.\n
It’s valid for 10 minutes. Enter this OTP to complete your account signup \n

The OneStopShop Team.
"""

    resend.Emails.send({
        "from": base.EMAIL_HOST_USER,
        "to": [user.email],
        "subject": subject,
        "text": message,
    })
