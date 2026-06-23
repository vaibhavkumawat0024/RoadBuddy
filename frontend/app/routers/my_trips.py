from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_token(request: Request) -> str | None:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/my-trips")
async def my_trips_page(request: Request):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")

    try:
        trips = await api_client.list_my_trips(token)
    except api_client.BackendError as e:
        return templates.TemplateResponse(request, "my_trips.html", {"request": request, "trips": [], "error": e.detail})

    return templates.TemplateResponse(request, "my_trips.html", {"request": request, "trips": trips, "error": None})


@router.post("/my-trips/delete/{trip_id}")
async def my_trips_delete(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Please log in again."})

    try:
        await api_client.delete_trip(token, trip_id)
        return {"ok": True}
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
