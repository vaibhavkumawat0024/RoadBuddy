"""
Provider Auth — RoadBuddy
---------------------------
JWT auth specifically for providers (separate from user auth).
Save as: app/provider/auth.py
"""

from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Provider

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/provider/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_provider_token(provider_id: int) -> str:
    """Create a JWT token for a provider, with a distinct 'type' claim."""
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": str(provider_id),
        "type": "provider",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_provider_token(token: str) -> int:
    """Decode token and return provider_id. Raises on invalid/expired/wrong type."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "provider":
            raise JWTError("Not a provider token")
        return int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired provider token")


def get_current_provider(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Provider:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    provider_id = decode_provider_token(token)
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


def get_provider_from_cookie(request, db: Session):
    """For page routes — read token from cookie instead of header."""
    token = request.cookies.get("provider_access_token")
    if not token:
        return None
    try:
        provider_id = decode_provider_token(token)
        return db.query(Provider).filter(Provider.id == provider_id).first()
    except Exception:
        return None
