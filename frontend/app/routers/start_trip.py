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

    booked_bus = None
    booked_train = None
    booked_flight = None
    booked_cab = None

    travel_date = date
    if not travel_date and trip_id:
        try:
            trip = await api_client.get_trip(token, trip_id)
            travel_date = trip.get("start_date", "")
        except Exception:
            pass

    if travel_date:
        try:
            # 1. Fetch transit bookings
            transit_bookings = await api_client.list_bookings(token)
            for b in transit_bookings:
                if b.get("status") == "confirmed" and b.get("travel_date") == travel_date:
                    mode = b.get("mode")
                    if not mode:
                        try:
                            mode = b.get("transport_option_id", "").split("_")[0]
                        except:
                            pass
                    if mode == "bus":
                        booked_bus = b
                    elif mode == "train":
                        booked_train = b
                    elif mode == "flight":
                        booked_flight = b

            # 2. Fetch cab bookings
            cab_bookings = await api_client.list_provider_bookings(token)
            for cb in cab_bookings:
                if cb.get("status") == "confirmed" and cb.get("travel_date") == travel_date:
                    booked_cab = cb
                    break
        except Exception:
            pass

    return templates.TemplateResponse(request, "start_trip.html", {
        "request": request,
        "origin": origin,
        "destination": destination,
        "backend_base_url": BACKEND_URL,
        "back_url": back_url,
        "trip_id": trip_id,
        "user": user,
        "date": travel_date or date,
        "booked_bus": booked_bus,
        "booked_train": booked_train,
        "booked_flight": booked_flight,
        "booked_cab": booked_cab,
    })