from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_token(request: Request) -> str | None:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/plan-trip")
async def plan_trip_page(request: Request, origin: str = "", destination: str = ""):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")

    vehicles = []
    try:
        vehicles = await api_client.list_vehicles(token)
    except api_client.BackendError:
        vehicles = []  # fine if user has none yet — bus/train/flight modes don't need one

    return templates.TemplateResponse(request, "plan_trip.html", {
        "request": request,
        "vehicles": vehicles,
        "origin": origin,
        "destination": destination
    })


class TripGenerateBody(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    budget_inr: float
    travel_mode: str
    vehicle_id: Optional[str] = None
    group_type: str
    num_people: int = 1


@router.post("/plan-trip/generate")
async def plan_trip_generate(request: Request, body: TripGenerateBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        result = await api_client.generate_trip(token, body.model_dump())
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
