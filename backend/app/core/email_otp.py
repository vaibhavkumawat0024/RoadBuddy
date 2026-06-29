import random
import time
import httpx
from app.core.config import settings

# email -> {"otp": str, "expires_at": float, "sent_at": float, ...extra fields
#           like "name" / "password" get bolted on by callers in users.py}
_otp_store: dict[str, dict] = {}

OTP_TTL_SECONDS = 300       # OTP is valid for 5 minutes
OTP_RESEND_COOLDOWN = 30    # must wait 30s between resend attempts


def send_otp_email(email: str, name: str, otp: str) -> bool:
    """Send OTP email via Resend API."""
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "RoadBuddy <onboarding@resend.dev>",  # Use your domain once verified
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


def generate_and_send_otp(email: str, name: str) -> bool:
    """
    Generate a 6-digit OTP, store it (with expiry) under _otp_store[email],
    and email it to the user.

    Raises:
        ValueError: if an OTP was already sent recently and the resend
            cooldown hasn't elapsed yet.
    """
    existing = _otp_store.get(email)
    now = time.time()

    if existing and now - existing.get("sent_at", 0) < OTP_RESEND_COOLDOWN:
        wait = int(OTP_RESEND_COOLDOWN - (now - existing["sent_at"]))
        raise ValueError(f"Please wait {wait}s before requesting another OTP")

    otp = f"{random.randint(0, 999999):06d}"

    # Note: this OVERWRITES any previously stashed fields (e.g. "name",
    # "password") for that email -- intentional, since a fresh OTP request
    # means a fresh registration attempt with possibly-updated data.
    _otp_store[email] = {
        "otp": otp,
        "expires_at": now + OTP_TTL_SECONDS,
        "sent_at": now,
    }

    return send_otp_email(email, name, otp)


def verify_otp(email: str, otp: str) -> bool:
    """
    Check a submitted OTP against the stored one, respecting expiry.
    Does NOT delete the record on success -- callers may still need to
    read other fields (e.g. "name", "password") off _otp_store[email]
    afterward. Call clear_otp() explicitly once done.
    """
    record = _otp_store.get(email)
    if record is None:
        return False

    if time.time() > record["expires_at"]:
        del _otp_store[email]
        return False

    return record["otp"] == otp


def clear_otp(email: str) -> None:
    """Remove a stored OTP/pending-registration record."""
    _otp_store.pop(email, None)