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


@router.get("/my-trips/api/{trip_id}")
async def get_trip_json(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    try:
        trip = await api_client.get_trip(token, trip_id)
        return trip
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/my-trips/{trip_id}/itinerary")
async def my_trip_itinerary_page(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        return RedirectResponse(url="/login")
    try:
        trip = await api_client.get_trip(token, trip_id)
    except api_client.BackendError as e:
        return RedirectResponse(url=f"/my-trips?error={e.detail}")

    booked_hotel_dict = None
    try:
        bookings = await api_client.list_bookings(token)
        dest = trip.get("destination", "").lower()
        start_date = trip.get("start_date", "")
        for b in bookings:
            if b.get("hotel_name") and b.get("status") == "confirmed" and b.get("check_in_date") == start_date:
                city = b.get("hotel_city", "").lower()
                if dest in city or city in dest:
                    booked_hotel_dict = {
                        "hotel_name": b.get("hotel_name"),
                        "check_in_date": b.get("check_in_date"),
                        "check_out_date": b.get("check_out_date"),
                        "num_rooms": b.get("num_rooms")
                    }
                    break
    except Exception:
        pass

    return templates.TemplateResponse(request, "trip_itinerary.html", {
        "request": request,
        "trip": trip,
        "booked_hotel": booked_hotel_dict
    })
