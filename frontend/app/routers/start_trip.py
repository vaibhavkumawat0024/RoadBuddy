from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.config import AUTH_COOKIE_NAME, BACKEND_URL
from app.core import api_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def _get_token(request: Request) -> str | None:
    return request.cookies.get(AUTH_COOKIE_NAME)

@router.get("/start-trip", response_class=HTMLResponse)
async def start_trip_page(request: Request, origin: str = "", destination: str = ""):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")
    
    user = None
    try:
        user = await api_client.get_profile(token)
    except Exception:
        pass

    return templates.TemplateResponse(request, "start_trip.html", {
        "request": request,
        "origin": origin,
        "destination": destination,
        "backend_base_url": BACKEND_URL,
        "back_url": "/plan-trip",
        "user": user,
    })