from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import (
    TransportSearch, TransportOption,
    TransportBooking, BookingOut
)
from app.services.transport_service import search_transport, calculate_total_fare, get_transport_option_by_id
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Booking

router = APIRouter()


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=list[TransportOption])
def search(
    data: TransportSearch,
    current_user: dict = Depends(get_current_user)
):
    """Search available buses, trains or flights."""
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Book a transport ticket.
    include_return is optional — False by default.
    """
    option = get_transport_option_by_id(data.transport_option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Transport option not found")

    if data.include_return and not data.return_date:
        raise HTTPException(
            status_code=400,
            detail="return_date is required when include_return is True"
        )

    fare = calculate_total_fare(
        going_fare=option.fare_inr,
        include_return=data.include_return,
        return_fare=option.fare_inr,
    )

    # Save to Neon DB
    booking = Booking(
        user_id             = int(current_user["user_id"]),
        transport_option_id = data.transport_option_id,
        passenger_name      = data.passenger_name,
        travel_date         = data.travel_date,
        include_return      = data.include_return,
        return_date         = data.return_date,
        going_fare_inr      = fare["going_fare_inr"],
        return_fare_inr     = fare["return_fare_inr"],
        total_fare_inr      = fare["total_fare_inr"],
        status              = "confirmed",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingOut(
        id                  = str(booking.id),
        user_id             = str(booking.user_id),
        transport_option_id = booking.transport_option_id,
        passenger_name      = booking.passenger_name,
        travel_date         = booking.travel_date,
        include_return      = booking.include_return,
        return_date         = booking.return_date,
        going_fare_inr      = booking.going_fare_inr,
        return_fare_inr     = booking.return_fare_inr,
        total_fare_inr      = booking.total_fare_inr,
        status              = booking.status,
        created_at          = str(booking.created_at),
    )


# ── My Bookings ───────────────────────────────────────────────────────────────

@router.get("/bookings", response_model=list[BookingOut])
def my_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for the logged in user."""
    bookings = db.query(Booking).filter(
        Booking.user_id == int(current_user["user_id"])
    ).all()

    return [
        BookingOut(
            id                  = str(b.id),
            user_id             = str(b.user_id),
            transport_option_id = b.transport_option_id,
            passenger_name      = b.passenger_name,
            travel_date         = b.travel_date,
            include_return      = b.include_return,
            return_date         = b.return_date,
            going_fare_inr      = b.going_fare_inr,
            return_fare_inr     = b.return_fare_inr,
            total_fare_inr      = b.total_fare_inr,
            status              = b.status,
            created_at          = str(b.created_at),
        )
        for b in bookings
    ]


# ── Cancel Booking ────────────────────────────────────────────────────────────

@router.patch("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a booking by ID."""
    booking = db.query(Booking).filter(
        Booking.id == int(booking_id),
        Booking.user_id == int(current_user["user_id"])
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")

    booking.status = "cancelled"
    db.commit()

    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking_id
    }