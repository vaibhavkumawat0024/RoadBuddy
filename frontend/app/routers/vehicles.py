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


@router.get("/vehicles")
async def vehicles_page(request: Request):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")

    vehicles = []
    try:
        vehicles = await api_client.list_vehicles(token)
    except api_client.BackendError:
        vehicles = []

    return templates.TemplateResponse(request, "vehicles.html", {
        "request": request,
        "vehicles": vehicles,
    })


class VehicleBody(BaseModel):
    name: str
    fuel_type: str
    category: str
    mileage_kmpl: float
    tank_capacity_litres: Optional[float] = None
    ev_range_km: Optional[float] = None


@router.post("/vehicles/add")
async def add_vehicle(request: Request, body: VehicleBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        result = await api_client.add_vehicle(token, body.model_dump())
        return result
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/vehicles/delete/{vehicle_id}")
async def delete_vehicle(request: Request, vehicle_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        await api_client.delete_vehicle(token, vehicle_id)
        return {"ok": True}
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})