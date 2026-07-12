from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.email_otp import generate_and_send_otp, verify_otp, clear_otp, _otp_store
from app.core.auth import hash_password, verify_password, create_access_token
from app.models.models import User
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "error": "Email already registered."
        })
    try:
        generate_and_send_otp(email, name)
    except ValueError as e:
        return templates.TemplateResponse(request, "register.html", {
            "error": str(e)
        })
    _otp_store[email]["name"] = name
    _otp_store[email]["password"] = hash_password(password)
    return templates.TemplateResponse(request, "verify_otp.html", {
        "email": email
    })


@router.post("/verify-otp", response_class=HTMLResponse)
def verify_otp_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db)
):
    record = _otp_store.get(email)
    if not record or not verify_otp(email, otp):
        return templates.TemplateResponse(request, "verify_otp.html", {
            "email": email,
            "error": "Invalid or expired OTP. Please try again."
        })
    user = User(
        name=record["name"],
        email=email,
        password_hash=record["password"]
    )
    db.add(user)
    db.commit()
    del _otp_store[email]
    return RedirectResponse("/login?success=Account created! Please login.", status_code=303)


@router.post("/resend-otp")
def resend_otp(
    email: str = Form(...)
):
    record = _otp_store.get(email)
    if not record:
        return {"success": False, "error": "Session expired. Please register again."}
    try:
        generate_and_send_otp(email, record.get("name", "Traveler"))
    except ValueError as e:
        return {"success": False, "error": str(e)}
    return {"success": True}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "login.html", {
        "success": success
    })


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid email or password."
        })
    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=86400,
        secure=not settings.debug,
        samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(request, "forgot_password.html", {
            "error": "No account registered with this email address."
        })
    try:
        generate_and_send_otp(email, user.name)
    except ValueError as e:
        return templates.TemplateResponse(request, "forgot_password.html", {
            "error": str(e)
        })
    return templates.TemplateResponse(request, "forgot_password_reset.html", {
        "email": email
    })


@router.post("/forgot-password/reset", response_class=HTMLResponse)
def forgot_password_reset_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return templates.TemplateResponse(request, "forgot_password.html", {
            "error": "No account registered with this email address."
        })
        
    if not verify_otp(email, otp):
        return templates.TemplateResponse(request, "forgot_password_reset.html", {
            "email": email,
            "error": "Invalid or expired OTP code. Please try again."
        })
        
    if len(new_password) < 8:
        return templates.TemplateResponse(request, "forgot_password_reset.html", {
            "email": email,
            "error": "New password must be at least 8 characters long."
        })
        
    user.password_hash = hash_password(new_password)
    db.commit()
    clear_otp(email)
    
    return RedirectResponse("/login?success=Password reset successfully! Please login with your new password.", status_code=303)