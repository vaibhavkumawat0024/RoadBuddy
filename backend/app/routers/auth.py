from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.models import User, Provider, Restaurant
from app.core.auth import (
    verify_password as verify_user_password,
    hash_password as hash_user_password,
    create_access_token as create_user_token
)
from app.provider.auth import (
    verify_password as verify_provider_password,
    hash_password as hash_provider_password,
    create_provider_token
)

router = APIRouter()

# ─── PYDANTIC REQUEST SCHEMAS ──────────────────────────────────────────
class SignupRequest(BaseModel):
    role: str # "traveler" | "provider" | "food_provider"
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    
    # Transport Provider specific
    company_name: Optional[str] = None
    fleet_type: Optional[str] = None # "cab" | "bus" | "train" | "flight"
    
    # Food Provider specific
    restaurant_name: Optional[str] = None
    location: Optional[str] = None
    license_number: Optional[str] = None

class LoginRequest(BaseModel):
    role: str # "traveler" | "provider" | "food_provider"
    email: EmailStr
    password: str


# ─── ENDPOINTS ──────────────────────────────────────────────────────────

@router.post("/signup")
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if payload.role == "traveler":
        # Check email in User table
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered as a traveler.")
            
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_user_password(payload.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        token = create_user_token({"sub": str(user.id)})
        
        # Set cookies
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "traveler",
            "name": user.name,
            "email": user.email
        }
        
    elif payload.role == "provider":
        # Check email in Provider table
        existing = db.query(Provider).filter(Provider.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered as a provider.")
            
        provider = Provider(
            company_name=payload.company_name or payload.name,
            contact_person=payload.name,
            email=payload.email,
            password_hash=hash_provider_password(payload.password),
            phone=payload.phone,
            service_type=payload.fleet_type or "cab"
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        token = create_provider_token(provider.id)
        
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="provider_access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "provider",
            "name": provider.contact_person,
            "email": provider.email
        }
        
    elif payload.role == "food_provider":
        # Check email in Provider table
        existing = db.query(Provider).filter(Provider.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered as a food provider.")
            
        provider = Provider(
            company_name=payload.restaurant_name or payload.name,
            contact_person=payload.name,
            email=payload.email,
            password_hash=hash_provider_password(payload.password),
            phone=payload.phone,
            service_type="restaurant",
            city=payload.location
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        # Create restaurant record
        restaurant = Restaurant(
            provider_id=provider.id,
            name=payload.restaurant_name or "Dhaba Partner",
            city=payload.location or "Unknown",
            address=payload.location or "Unknown",
            contact_number=payload.phone
        )
        db.add(restaurant)
        db.commit()
        
        token = create_provider_token(provider.id)
        
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="food_provider_access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "food_provider",
            "name": provider.contact_person,
            "email": provider.email
        }
        
    else:
        raise HTTPException(status_code=400, detail="Invalid user role selected.")


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    if payload.role == "traveler":
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not verify_user_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        token = create_user_token({"sub": str(user.id)})
        
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "traveler",
            "name": user.name,
            "email": user.email
        }
        
    elif payload.role == "provider":
        provider = db.query(Provider).filter(
            Provider.email == payload.email,
            Provider.service_type != "restaurant"
        ).first()
        if not provider or not verify_provider_password(payload.password, provider.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        token = create_provider_token(provider.id)
        
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="provider_access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "provider",
            "name": provider.contact_person,
            "email": provider.email
        }
        
    elif payload.role == "food_provider":
        provider = db.query(Provider).filter(
            Provider.email == payload.email,
            Provider.service_type == "restaurant"
        ).first()
        if not provider or not verify_provider_password(payload.password, provider.provider_hash if hasattr(provider, 'provider_hash') else provider.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        token = create_provider_token(provider.id)
        
        response.set_cookie(key="roadbuddy_token", value=token, httponly=True, samesite="lax", path="/")
        response.set_cookie(key="food_provider_access_token", value=token, httponly=False, samesite="lax", path="/")
        
        return {
            "role": "food_provider",
            "name": provider.contact_person,
            "email": provider.email
        }
        
    else:
        raise HTTPException(status_code=400, detail="Invalid user role selected.")


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    # Read the token
    token = request.cookies.get("roadbuddy_token")
    if not token:
        token = (
            request.cookies.get("access_token") or
            request.cookies.get("provider_access_token") or
            request.cookies.get("food_provider_access_token")
        )
    if not token:
        # Check headers
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    # Attempt to decode as user token first
    from jose import jwt, JWTError
    from app.core.config import settings
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        # Ensure it has no "type" claim (which is unique to provider tokens)
        if user_id and payload.get("type") != "provider":
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                return {
                    "role": "traveler",
                    "name": user.name,
                    "email": user.email
                }
    except JWTError:
        pass
        
    # If decoding fails or type matches provider, attempt decode as provider
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") == "provider":
            provider_id = int(payload["sub"])
            provider = db.query(Provider).filter(Provider.id == provider_id).first()
            if provider:
                role = "food_provider" if provider.service_type == "restaurant" else "provider"
                return {
                    "role": role,
                    "name": provider.contact_person,
                    "email": provider.email
                }
    except JWTError:
        pass
        
    raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="roadbuddy_token", path="/")
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="provider_access_token", path="/")
    response.delete_cookie(key="food_provider_access_token", path="/")
    return {"detail": "Logged out successfully"}
