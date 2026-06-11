from fastapi import APIRouter, HTTPException, Depends
from app.schemas.schemas import (
    TransportSearch, TransportOption,
    TransportBooking, BookingOut
)
from app.services.transport_service import search_transport, calculate_total_fare
from app.core.auth import get_current_user
from datetime import datetime

router = APIRouter()

# In-memory store (replace with DB later)
_bookings: dict = {}


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=list[TransportOption])
def search(data: TransportSearch, current_user: dict = Depends(get_current_user)):
    """
    Search available buses, trains or flights.
    Pass origin, destination, mode and travel_date.
    Returns list of available options with fares.
    """
    results = search_transport(
        origin=data.origin,
        destination=data.destination,
        mode=data.mode,
    )
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No {data.mode} options found for this route"
        )
    return results


# ── Book ──────────────────────────────────────────────────────────────────────

@router.post("/book", response_model=BookingOut, status_code=201)
def book_ticket(
    data: TransportBooking,
    current_user: dict = Depends(get_current_user)
):
    """
    Book a transport ticket.
    include_return is optional — False by default.
    If include_return is True, provide return_date too.
    Total cost = going fare only OR going + return fare.
    """
    # Find the selected transport option from mock data
    # In production: fetch from DB using data.transport_option_id
    all_options = (
        search_transport("any", "any", "bus") +
        search_transport("any", "any", "train") +
        search_transport("any", "any", "flight")
    )
    option = next(
        (o for o in all_options if o.id == data.transport_option_id),
        None
    )
    if not option:
        raise HTTPException(status_code=404, detail="Transport option not found")

    # Validate return date if include_return is True
    if data.include_return and not data.return_date:
        raise HTTPException(
            status_code=400,
            detail="return_date is required when include_return is True"
        )

    # Calculate fare
    fare = calculate_total_fare(
        going_fare=option.fare_inr,
        include_return=data.include_return,
        return_fare=option.fare_inr,  # same fare for return
    )

    # Create booking
    booking_id = f"bk_{len(_bookings) + 1}"
    booking = {
        "id": booking_id,
        "user_id": current_user["user_id"],
        "transport_option_id": data.transport_option_id,
        "passenger_name": data.passenger_name,
        "travel_date": data.travel_date,
        "include_return": data.include_return,
        "return_date": data.return_date,
        "going_fare_inr": fare["going_fare_inr"],
        "return_fare_inr": fare["return_fare_inr"],
        "total_fare_inr": fare["total_fare_inr"],
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }
    _bookings[booking_id] = booking
    return BookingOut(**booking)


# ── My Bookings ───────────────────────────────────────────────────────────────

@router.get("/bookings", response_model=list[BookingOut])
def my_bookings(current_user: dict = Depends(get_current_user)):
    """
    Get all bookings for the logged in user.
    """
    user_id = current_user["user_id"]
    return [
        BookingOut(**b)
        for b in _bookings.values()
        if b["user_id"] == user_id
    ]


# ── Cancel Booking ────────────────────────────────────────────────────────────

@router.patch("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a booking by ID.
    """
    booking = _bookings.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")

    _bookings[booking_id]["status"] = "cancelled"
    return {"message": "Booking cancelled successfully", "booking_id": booking_id}