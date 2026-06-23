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


@router.get("/bookings", response_class=HTMLResponse)
async def bookings_page(request: Request):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")

    # Fetch existing transport bookings to display
    bookings = []
    try:
        bookings = await api_client.list_bookings(token)
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "bookings.html",
        {"request": request, "bookings": bookings},
    )


# ── Hotels ─────────────────────────────────────────────────────────────────

class HotelSearchBody(BaseModel):
    city: str
    num_rooms: int = 1
    num_guests: int = 1


@router.post("/bookings/hotels/search")
async def search_hotels(request: Request, body: HotelSearchBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.search_hotels(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class HotelBookBody(BaseModel):
    hotel_id: int
    check_in_date: str
    check_out_date: str
    num_rooms: int = 1
    num_guests: int = 1


@router.post("/bookings/hotels/book")
async def book_hotel(request: Request, body: HotelBookBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.book_hotel(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Trains ─────────────────────────────────────────────────────────────────

class TrainSearchBody(BaseModel):
    origin: str
    destination: str
    num_seats: int = 1


@router.post("/bookings/trains/search")
async def search_trains(request: Request, body: TrainSearchBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.search_trains(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class TrainBookBody(BaseModel):
    train_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


@router.post("/bookings/trains/book")
async def book_train(request: Request, body: TrainBookBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.book_train(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Buses ──────────────────────────────────────────────────────────────────

class BusSearchBody(BaseModel):
    origin: str
    destination: str
    num_seats: int = 1


@router.post("/bookings/buses/search")
async def search_buses(request: Request, body: BusSearchBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.search_buses(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class BusBookBody(BaseModel):
    bus_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


@router.post("/bookings/buses/book")
async def book_bus(request: Request, body: BusBookBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.book_bus(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Flights ────────────────────────────────────────────────────────────────

class FlightSearchBody(BaseModel):
    origin: str
    destination: str
    num_seats: int = 1


@router.post("/bookings/flights/search")
async def search_flights(request: Request, body: FlightSearchBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.search_flights(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class FlightBookBody(BaseModel):
    flight_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


@router.post("/bookings/flights/book")
async def book_flight(request: Request, body: FlightBookBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.book_flight(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Transport (Buses/Trains/Flights options search) ─────────────────────────

class TransportSearchBody(BaseModel):
    origin: str
    destination: str
    mode: str


@router.post("/bookings/transport/search")
async def search_transport(request: Request, body: TransportSearchBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.search_transport(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class TransportBookBody(BaseModel):
    transport_option_id: str
    passenger_name: str
    travel_date: str
    include_return: bool = False
    return_date: Optional[str] = None


@router.post("/bookings/transport/book")
async def book_transport(request: Request, body: TransportBookBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.book_transport(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/bookings/transport/list")
async def list_transport_bookings(request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.list_bookings(token)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.patch("/bookings/transport/{booking_id}/cancel")
async def cancel_transport_booking(request: Request, booking_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.cancel_booking(token, booking_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Rider Provider Booking management & Tracking Proxies ──────────────────────

@router.get("/my-bookings", response_class=HTMLResponse)
async def my_bookings_page(request: Request):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)

    user = None
    try:
        user = await api_client.get_profile(token)
    except Exception:
        pass

    bookings = []
    try:
        bookings = await api_client.list_provider_bookings(token)
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "my_bookings.html",
        {
            "request": request,
            "user": user,
            "bookings": bookings,
            "has_unread_bookings": False
        },
    )


@router.post("/cancel-booking/{booking_id}")
async def cancel_booking(booking_id: int, request: Request):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)

    try:
        await api_client.cancel_provider_booking(token, booking_id)
    except Exception:
        pass

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/my-bookings", status_code=303)


@router.get("/bookings/active-enroute")
async def get_active_enroute_bookings(request: Request, user_id: int):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    try:
        return await api_client.list_active_enroute_bookings(token, user_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/bookings/{booking_id}/track")
async def track_provider_booking_route(request: Request, booking_id: int):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    try:
        return await api_client.track_provider_booking(token, booking_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/bookings/unread-check")
async def unread_check_route(request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    try:
        return await api_client.check_unread_provider_bookings(token)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
