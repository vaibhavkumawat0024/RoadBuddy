from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import asyncio
from app.schemas.schemas import (
    TransportSearch, TransportOption,
    TransportBooking, BookingOut, TransportMode
)
from app.services.transport_service import search_transport, calculate_total_fare, get_transport_option_by_id
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Booking
from app.services import duffel_client

router = APIRouter()


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=list[TransportOption])
async def search(
    data: TransportSearch,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search available buses, trains or flights."""
    if data.mode == TransportMode.flight or data.mode == "flight":
        try:
            results = await duffel_client.search_flights(
                origin=data.origin,
                destination=data.destination,
                travel_date=data.travel_date,
                num_seats=1
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Duffel Flight Search Error: {str(e)}"
            )
    else:
        results = search_transport(
            origin=data.origin,
            destination=data.destination,
            mode=data.mode,
            db=db
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
    option = get_transport_option_by_id(data.transport_option_id, db)
    if not option:
        raise HTTPException(status_code=404, detail="Transport option not found")

    if data.include_return and not data.return_date:
        raise HTTPException(
            status_code=400,
            detail="return_date is required when include_return is True"
        )

    # Lock and update seat count in DB
    try:
        parts = data.transport_option_id.split("_")
        mode = parts[0]
        item_id = int(parts[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid transport option ID format")

    if mode == "bus":
        from app.models.models import Bus
        bus = db.query(Bus).filter(Bus.id == item_id).with_for_update().first()
        if not bus:
            raise HTTPException(status_code=404, detail="Bus not found")
        if bus.seats_available < 1:
            raise HTTPException(status_code=400, detail="No seats available on this bus")
        bus.seats_booked += 1
    elif mode == "train":
        from app.models.models import Train
        train = db.query(Train).filter(Train.id == item_id).with_for_update().first()
        if not train:
            raise HTTPException(status_code=404, detail="Train not found")
        if train.seats_available < 1:
            raise HTTPException(status_code=400, detail="No seats available on this train")
        train.seats_booked += 1
    elif mode == "flight":
        from app.models.models import Flight
        flight = db.query(Flight).filter(Flight.id == item_id).with_for_update().first()
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found")
        if flight.seats_available < 1:
            raise HTTPException(status_code=400, detail="No seats available on this flight")
        flight.seats_booked += 1

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
        selected_seats      = data.selected_seats,
        travel_class        = data.travel_class,
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
        selected_seats      = booking.selected_seats,
        travel_class        = booking.travel_class,
    )


# ── My Bookings ───────────────────────────────────────────────────────────────

@router.get("/bookings", response_model=list[BookingOut])
async def my_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for the logged in user."""
    from app.models.models import HotelBooking
    
    uid = int(current_user["user_id"])
    
    bookings = db.query(Booking).filter(
        Booking.user_id == uid
    ).all()

    hotel_bookings = db.query(HotelBooking).filter(
        HotelBooking.user_id == uid
    ).all()

    # Concurrent fetch of live Duffel flight order statuses
    duffel_statuses = {}
    flight_bookings = [b for b in bookings if getattr(b, "duffel_order_id", None)]
    if flight_bookings:
        tasks = [duffel_client.get_flight_order(b.duffel_order_id) for b in flight_bookings]
        try:
            orders_data = await asyncio.gather(*tasks, return_exceptions=True)
            for b, order in zip(flight_bookings, orders_data):
                if not isinstance(order, Exception):
                    is_cancelled = bool(order.get("cancelled_at"))
                    new_status = "cancelled" if is_cancelled else "confirmed"
                    if b.status != new_status:
                        b.status = new_status
                        db.commit()
                    duffel_statuses[b.duffel_order_id] = new_status
        except Exception as e:
            print(f"Error fetching live Duffel order statuses: {e}")

    results = []
    
    # 1. Add transit bookings
    for b in bookings:
        opt = get_transport_option_by_id(b.transport_option_id, db)
        mode = None
        operator = None
        origin = None
        destination = None
        if opt:
            mode = opt.mode
            operator = opt.operator
            origin = opt.origin_station_name or opt.origin
            destination = opt.destination_station_name or opt.destination
        else:
            try:
                parts = b.transport_option_id.split("_")
                mode = parts[0]
            except Exception:
                pass

        results.append(
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
                mode                = mode,
                transport_option_operator = operator,
                origin              = origin,
                destination         = destination,
                selected_seats      = b.selected_seats,
                travel_class        = b.travel_class,
            )
        )

    # 2. Add hotel bookings
    for h in hotel_bookings:
        results.append(
            BookingOut(
                id                  = f"hotel_{h.id}",
                user_id             = str(h.user_id),
                transport_option_id = f"hotel_{h.hotel_id}",
                passenger_name      = "Self",
                travel_date         = h.check_in_date,
                include_return      = False,
                return_date         = h.check_out_date,
                going_fare_inr      = h.total_price_inr,
                return_fare_inr     = 0.0,
                total_fare_inr      = h.total_price_inr,
                status              = h.status,
                created_at          = str(h.created_at),
                mode                = None,
                transport_option_operator = None,
                origin              = h.hotel.city,
                destination         = h.hotel.city,
                hotel_name          = h.hotel.name,
                hotel_city          = h.hotel.city,
                check_in_date       = h.check_in_date,
                check_out_date      = h.check_out_date,
                num_guests          = h.num_guests,
                num_rooms           = h.num_rooms,
                total_price_inr     = h.total_price_inr,
            )
        )

    # Sort combined bookings by created_at desc
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results


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