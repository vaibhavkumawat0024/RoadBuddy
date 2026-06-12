import time

_otp_store: dict = {}
DEFAULT_OTP = "1234"

def generate_otp(email: str) -> str:
    _otp_store[email] = {
        "otp": DEFAULT_OTP,
        "expires": time.time() + 300
    }
    return DEFAULT_OTP

def verify_otp(email: str, otp: str) -> bool:
    record = _otp_store.get(email)
    if not record:
        return False
    if time.time() > record["expires"]:
        del _otp_store[email]
        return False
    if record["otp"] != otp:
        return False
    del _otp_store[email]
    return True