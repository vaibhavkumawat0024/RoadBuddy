from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.core import api_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


from app.core.config import AUTH_COOKIE_NAME

def _get_token(request: Request) -> str | None:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/dashboard")
def dashboard_page(request: Request):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


# ── Proxy endpoints used by the dashboard's JS widgets ──────────────────────
# These exist purely to avoid CORS issues calling the backend directly from
# the browser (backend's allowed_origins doesn't include port 3000).

class ChatBody(BaseModel):
    message: str
    history: Optional[list] = []


@router.post("/dashboard/chat")
async def proxy_chat(request: Request, body: ChatBody):
    token = _get_token(request)
    try:
        result = await api_client.trip_chat(body.message, body.history, token=token)
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class WaypointBody(BaseModel):
    origin: str
    destination: str
    preferences: Optional[list] = []


@router.post("/dashboard/waypoints")
async def proxy_waypoints(body: WaypointBody):
    try:
        result = await api_client.suggest_waypoints(
            body.origin, body.destination, body.preferences
        )
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class SafetyBody(BaseModel):
    origin: str
    destination: str
    travel_date: str


@router.post("/dashboard/safety-check")
async def proxy_safety(body: SafetyBody):
    try:
        result = await api_client.safety_check(
            body.origin, body.destination, body.travel_date
        )
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class RecommendBody(BaseModel):
    home_city: str
    budget_inr: float
    interests: Optional[list] = ["sightseeing"]


@router.post("/dashboard/recommendations")
async def proxy_recommendations(body: RecommendBody):
    try:
        result = await api_client.trip_recommendations(
            body.home_city, body.budget_inr, body.interests
        )
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
