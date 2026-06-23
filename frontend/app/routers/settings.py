from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_token(request: Request) -> str | None:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/settings")
async def settings_page(request: Request):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")

    profile = None
    try:
        profile = await api_client.get_profile(token)
    except api_client.BackendError:
        profile = None  # show the page anyway; template handles missing profile

    return templates.TemplateResponse(request, "settings.html", {
        "request": request,
        "profile": profile,
    })


class ProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


@router.patch("/settings/profile")
async def update_profile(request: Request, body: ProfileUpdateBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        result = await api_client.update_profile(token, name=body.name, email=body.email)
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class PasswordChangeBody(BaseModel):
    current_password: str
    new_password: str


@router.post("/settings/password", status_code=204)
async def change_password(request: Request, body: PasswordChangeBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        await api_client.change_password(token, body.current_password, body.new_password)
        return Response(status_code=204)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/profile-json")
async def get_profile_json(request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not logged in"})
    try:
        return await api_client.get_profile(token)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})