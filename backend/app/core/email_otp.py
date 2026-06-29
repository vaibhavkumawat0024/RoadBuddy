import httpx
from app.core.config import settings

def send_otp_email(email: str, name: str, otp: str) -> bool:
    """Send OTP email via Resend API."""
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "RoadBuddy <onboarding@resend.dev>", # Use your domain once verified
            "to": [email],
            "subject": f"{otp} is your RoadBuddy verification code",
            "html": f"<strong>Hi {name}</strong>, your code is {otp}"
        }
        
        with httpx.Client() as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
        return True

    except Exception as e:
        print(f"API Email failed: {e}")
        return False