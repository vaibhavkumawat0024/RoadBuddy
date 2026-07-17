import random
import time
import httpx
from app.core.config import settings

# email -> {"otp": str, "expires_at": float, "sent_at": float, ...extra fields
#           like "name" / "password" get bolted on by callers in users.py}
_otp_store: dict[str, dict] = {}

OTP_TTL_SECONDS = 300       # OTP is valid for 5 minutes
OTP_RESEND_COOLDOWN = 30    # must wait 30s between resend attempts


def send_otp_email(email: str, name: str, otp: str, otp_type: str = "verification") -> bool:
    """Send OTP email via Brevo's transactional email API with template based on type."""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": settings.brevo_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if otp_type == "payment":
            subject = f"🛡️ {otp} is your RoadBuddy Payment OTP"
            html_content = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; color: #1e293b; background-color: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
              <div style="text-align: center; margin-bottom: 28px;">
                <h1 style="color: #dc2626; font-size: 28px; margin: 0; font-weight: 800; letter-spacing: -0.5px;">RoadBuddy</h1>
                <span style="font-size: 11px; color: #b91c1c; text-transform: uppercase; font-weight: 700; letter-spacing: 1.5px; background-color: #fef2f2; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-top: 6px;">
                  💳 Secure Payment Authorization
                </span>
              </div>
              
              <div style="font-size: 15px; line-height: 1.6; color: #334155;">
                <p>Hi <strong>{name}</strong>,</p>
                <p>We received a request to authorize a payment transaction on your RoadBuddy account. Please use the following One-Time Password (OTP) to complete your checkout:</p>
                
                <div style="background: #fef2f2; border: 1px dashed #fca5a5; padding: 20px; border-radius: 12px; font-size: 36px; font-weight: 800; text-align: center; letter-spacing: 8px; margin: 24px 0; color: #991b1b; font-family: 'Courier New', Courier, monospace; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
                  {otp}
                </div>
                
                <p style="font-size: 13px; color: #64748b; margin-top: 16px; background-color: #fffbeb; padding: 14px; border-radius: 8px; border-left: 4px solid #f59e0b; line-height: 1.5;">
                  <strong>⚠️ CRITICAL SECURITY WARNING:</strong><br>
                  Never share this OTP with anyone. RoadBuddy support team, restaurant partners, or payment agents will <strong>NEVER</strong> contact you via phone, email, or WhatsApp to request this code. If someone asks for this OTP, they are attempting to defraud you.
                </p>

                <div style="margin-top: 24px; padding: 16px; background-color: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9;">
                  <span style="font-weight: 700; font-size: 13px; color: #475569; display: block; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">✓ Safety Checklist:</span>
                  <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #64748b; line-height: 1.5;">
                    <li>Check that the booking/order amount matches your screen.</li>
                    <li>Ensure you are transacting on the official RoadBuddy application or website.</li>
                    <li>This OTP will expire in <strong>5 minutes</strong>.</li>
                  </ul>
                </div>
              </div>
              
              <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 28px 0;" />
              
              <div style="text-align: center; font-size: 12px; color: #94a3b8; line-height: 1.4;">
                <p>If you did not initiate this payment, please contact our 24/7 Security Helpline immediately.</p>
                <p>© {time.strftime("%Y")} RoadBuddy Payments. All rights reserved.</p>
              </div>
            </div>
            """
        else:
            # Login / Verification / Registration OTP
            subject = f"🔑 {otp} is your RoadBuddy verification code"
            html_content = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; color: #1e293b; background-color: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
              <div style="text-align: center; margin-bottom: 28px;">
                <h1 style="color: #2563eb; font-size: 28px; margin: 0; font-weight: 800; letter-spacing: -0.5px;">RoadBuddy</h1>
                <span style="font-size: 11px; color: #1d4ed8; text-transform: uppercase; font-weight: 700; letter-spacing: 1.5px; background-color: #eff6ff; padding: 6px 12px; border-radius: 6px; display: inline-block; margin-top: 6px;">
                  🔑 Secure Account Login
                </span>
              </div>
              
              <div style="font-size: 15px; line-height: 1.6; color: #334155;">
                <p>Hi <strong>{name}</strong>,</p>
                <p>Welcome back to RoadBuddy! Let's get you signed in. Use the verification code below to authorize your login request:</p>
                
                <div style="background: #f8fafc; border: 1px dashed #cbd5e1; padding: 20px; border-radius: 12px; font-size: 36px; font-weight: 800; text-align: center; letter-spacing: 8px; margin: 24px 0; color: #1e3a8a; font-family: 'Courier New', Courier, monospace; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
                  {otp}
                </div>
                
                <p style="font-size: 13px; color: #64748b; margin-top: 16px; background-color: #f1f5f9; padding: 12px; border-radius: 8px; line-height: 1.4;">
                  <strong>🔒 Security Tip:</strong><br>
                  This OTP is valid for <strong>5 minutes</strong>. If you did not request this login code, your password might have been compromised. We recommend updating your credentials immediately.
                </p>
              </div>
              
              <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 28px 0;" />
              
              <div style="text-align: center; font-size: 12px; color: #94a3b8; line-height: 1.4;">
                <p>Need help? Reach out to us at <a href="mailto:support@roadbuddy.com" style="color: #2563eb; text-decoration: none;">support@roadbuddy.com</a></p>
                <p>© {time.strftime("%Y")} RoadBuddy. All rights reserved.</p>
              </div>
            </div>
            """

        payload = {
            "sender": {"name": "RoadBuddy", "email": settings.brevo_sender_email},
            "to": [{"email": email, "name": name}],
            "subject": subject,
            "htmlContent": html_content,
        }

        with httpx.Client() as client:
            res = client.post(url, headers=headers, json=payload)
            if res.status_code >= 400:
                print(f"API Email failed: {res.status_code} {res.text}")
                return False
        return True

    except Exception as e:
        print(f"API Email failed: {e}")
        return False


def generate_and_send_otp(email: str, name: str, otp_type: str = "verification") -> bool:
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

    return send_otp_email(email, name, otp, otp_type)


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