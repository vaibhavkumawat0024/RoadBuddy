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
async def start_trip_page(request: Request, origin: str = "", destination: str = "", trip_id: str = "", date: str = ""):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")
    
    user = None
    try:
        user = await api_client.get_profile(token)
    except Exception:
        pass

    back_url = f"/my-trips/{trip_id}/itinerary" if trip_id else "/plan-trip"

    return templates.TemplateResponse(request, "start_trip.html", {
        "request": request,
        "origin": origin,
        "destination": destination,
        "backend_base_url": BACKEND_URL,
        "back_url": back_url,
        "trip_id": trip_id,
        "user": user,
        "date": date,
    })