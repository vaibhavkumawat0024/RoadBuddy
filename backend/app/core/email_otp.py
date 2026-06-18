"""
Email OTP Service — RoadBuddy
------------------------------
Sends real OTP emails using Gmail SMTP.
Replaces the hardcoded 1234 OTP.
"""

import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.core.config import settings

# ── In-memory OTP store ───────────────────────────────────────────────────────
# Format: { email: { otp, expires_at, name, password } }
_otp_store = {}


# ── Generate OTP ──────────────────────────────────────────────────────────────

def generate_otp(email: str) -> str:
    """Generate a 6-digit OTP and store it with 10 minute expiry."""
    if email in _otp_store:
        record = _otp_store[email]
        if "last_requested_at" in record:
            time_since_last = datetime.now() - record["last_requested_at"]
            if time_since_last.total_seconds() < 60:
                raise ValueError("Please wait 60 seconds before requesting a new OTP.")

    otp = str(secrets.randbelow(900000) + 100000)
    existing_record = _otp_store.get(email, {})
    name = existing_record.get("name")
    password = existing_record.get("password")

    _otp_store[email] = {
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=10),
        "last_requested_at": datetime.now(),
        "name": name,
        "password": password
    }
    return otp


def verify_otp(email: str, otp: str) -> bool:
    """Verify OTP — returns True if valid and not expired."""
    record = _otp_store.get(email)
    if not record:
        return False
    if record["otp"] != otp:
        return False
    if datetime.now() > record["expires_at"]:
        del _otp_store[email]
        return False
    return True


def clear_otp(email: str):
    """Remove OTP after successful verification."""
    if email in _otp_store:
        del _otp_store[email]


# ── Send OTP Email ────────────────────────────────────────────────────────────

def send_otp_email(email: str, name: str, otp: str) -> bool:
    """Send OTP email via Gmail SMTP. Returns True if sent successfully."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{otp} is your RoadBuddy verification code"
        msg["From"]    = settings.mail_from
        msg["To"]      = email

        # Plain text version
        text = f"""
Hi {name},

Your RoadBuddy verification code is: {otp}

This code expires in 10 minutes.

If you did not request this, please ignore this email.

— RoadBuddy Team
        """.strip()

        # HTML version
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f5f5f0;font-family:system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;border:1px solid #e5e5e5;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:#1D9E75;padding:28px 32px;text-align:center;">
              <h1 style="margin:0;color:#fff;font-size:22px;font-weight:600;">🚗 RoadBuddy</h1>
              <p style="margin:6px 0 0;color:#d4f0e8;font-size:13px;">AI-Powered Road Trip Planner</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 8px;font-size:15px;color:#1a1a1a;">Hi <strong>{name}</strong>,</p>
              <p style="margin:0 0 24px;font-size:14px;color:#555;line-height:1.6;">
                Use the verification code below to complete your registration on RoadBuddy.
              </p>

              <!-- OTP Box -->
              <div style="background:#f0faf6;border:2px dashed #1D9E75;border-radius:10px;padding:20px;text-align:center;margin:0 0 24px;">
                <p style="margin:0 0 4px;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1px;">Your verification code</p>
                <p style="margin:0;font-size:40px;font-weight:700;color:#1D9E75;letter-spacing:12px;">{otp}</p>
                <p style="margin:8px 0 0;font-size:12px;color:#888;">Expires in 10 minutes</p>
              </div>

              <p style="margin:0 0 8px;font-size:13px;color:#888;">
                If you did not create a RoadBuddy account, please ignore this email.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8f8f6;padding:16px 32px;border-top:1px solid #e5e5e5;text-align:center;">
              <p style="margin:0;font-size:12px;color:#aaa;">
                © 2026 RoadBuddy · Plan smarter, travel better 🚗
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
        """.strip()

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.mail_username, settings.mail_password)
            server.sendmail(settings.mail_from, email, msg.as_string())

        return True

    except Exception as e:
        print(f"Email send failed: {e}")
        return False


# ── Main function called from auth_pages.py ───────────────────────────────────

def generate_and_send_otp(email: str, name: str) -> bool:
    """Generate OTP and send email. Returns True if email sent successfully."""
    otp = generate_otp(email)
    sent = send_otp_email(email, name, otp)
    if not sent:
        # Fallback — store OTP but warn
        if settings.debug:
            print(f"WARNING: Email failed for {email}. OTP is {otp} (dev fallback)")
        else:
            print(f"WARNING: Email failed for {email} (dev fallback)")
    return sent
