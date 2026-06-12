from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.otp import generate_otp, verify_otp, _otp_store
from app.core.auth import hash_password, verify_password, create_access_token
from app.models.models import User

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
    generate_otp(email)
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
    if not record or record["otp"] != otp:
        return templates.TemplateResponse(request, "verify_otp.html", {
            "email": email,
            "error": "Invalid OTP. Please enter 1234."
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
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response