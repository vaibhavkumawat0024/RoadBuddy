from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_token(request: Request) -> Optional[str]:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/fuel", response_class=HTMLResponse)
async def fuel_page(request: Request):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")

    vehicles = []
    try:
        vehicles = await api_client.list_vehicles(token)
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "fuel.html",
        {"request": request, "vehicles": vehicles},
    )


class FuelCalcBody(BaseModel):
    origin: str
    destination: str
    vehicle_id: str
    include_return: bool = False


@router.post("/fuel/calculate")
async def calculate_fuel(request: Request, body: FuelCalcBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.calculate_fuel(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/fuel/prices")
async def get_fuel_prices():
    try:
        return await api_client.get_fuel_prices()
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/fuel/toll-estimate")
async def get_toll_estimate(origin: str, destination: str, vehicle_category: str = "car"):
    try:
        return await api_client.get_toll_estimate(origin, destination, vehicle_category)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
