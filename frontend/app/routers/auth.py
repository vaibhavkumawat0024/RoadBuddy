from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import urllib.parse

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME, COOKIE_SECURE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request, "error": None})


@router.post("/register")
async def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        await api_client.register_user(name, email, password)
    except api_client.BackendError as e:
        return templates.TemplateResponse(request, "register.html", {"request": request, "error": e.detail})
    # Registration triggers an OTP email; move to the verify step.
    encoded_email = urllib.parse.quote(email)
    return RedirectResponse(
        url=f"/verify-otp?email={encoded_email}", status_code=303
    )


@router.get("/verify-otp")
def verify_otp_page(request: Request, email: str = ""):
    return templates.TemplateResponse(request, "verify_otp.html", {"request": request, "email": email, "error": None})


@router.post("/verify-otp")
async def verify_otp_submit(
    request: Request, email: str = Form(...), otp: str = Form(...)
):
    try:
        await api_client.verify_otp(email, otp)
    except api_client.BackendError as e:
        return templates.TemplateResponse(
            request, "verify_otp.html",
            {"request": request, "email": email, "error": e.detail},
        )
    return RedirectResponse(url="/login?verified=1", status_code=303)


@router.get("/login")
def login_page(request: Request, verified: str = ""):
    return templates.TemplateResponse(
        request, "login.html",
        {"request": request, "error": None, "just_verified": bool(verified)},
    )


@router.post("/login")
async def login_submit(
    request: Request, email: str = Form(...), password: str = Form(...)
):
    try:
        data = await api_client.login_user(email, password)
    except api_client.BackendError as e:
        return templates.TemplateResponse(
            request, "login.html",
            {"request": request, "error": e.detail, "just_verified": False},
        )

    token = data.get("access_token") if data else None
    response = RedirectResponse(url="/dashboard", status_code=303)
    if token:
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            max_age=60 * 60 * 24,  # 24h, matches backend JWT expiry
        )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response
