"""
Travel Booking Router — RoadBuddy
-------------------------------------
Search & book hotels, trains, buses, flights — all internal, no external APIs.
Save as: app/routers/booking.py

Register in main.py:
    from app.routers import booking
    app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Hotel, HotelBooking, HotelReview, Train, TrainBooking, Bus, BusBooking, Flight, FlightBooking
from app.schemas.booking_schemas import (
    HotelSearchRequest, HotelResult, HotelBookingRequest, HotelBookingOut,
    HotelReviewCreate, HotelReviewOut,
    TrainSearchRequest, TrainResult, TrainBookingRequest, TrainBookingOut,
    BusSearchRequest, BusResult, BusBookingRequest, BusBookingOut,
    FlightSearchRequest, FlightResult, FlightBookingRequest, FlightBookingOut,
)
from app.services import duffel_client

router = APIRouter()


def escape_like(text: str) -> str:
    return text.replace('/', '//').replace('%', '/%').replace('_', '/_')


# ── Hotels ─────────────────────────────────────────────────────────────────

@router.post("/hotels/search", response_model=list[HotelResult])
async def search_hotels(
    data: HotelSearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    check_in = data.check_in_date
    check_out = data.check_out_date
    if not check_in:
        check_in = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not check_out:
        check_out = (datetime.strptime(check_in, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        
    try:
        results = await duffel_client.search_hotels(
            city=data.city,
            check_in=check_in,
            check_out=check_out,
            num_rooms=data.num_rooms,
            num_guests=1
        )
        return results
    except Exception as e:
        print(f"Duffel Stays search encountered an error (e.g. 403 Forbidden, product not enabled, or connection issue). Falling back to local mock data. Error: {e}")
        escaped_city = escape_like(data.city)
        hotels = db.query(Hotel).filter(Hotel.city.ilike(f"%{escaped_city}%", escape='/')).all()
        return [
            HotelResult(
                id=h.id, name=h.name, city=h.city, address=h.address,
                star_rating=h.star_rating, price_per_night_inr=h.price_per_night_inr,
                rooms_available=h.rooms_available, amenities=h.amenities,
                avg_rating=h.avg_rating if h.avg_rating is not None else 0.0,
                total_reviews=h.total_reviews if h.total_reviews is not None else 0,
            )
            for h in hotels if h.rooms_available >= data.num_rooms
        ]


@router.get("/hotels/{hotel_id}/reviews", response_model=list[HotelReviewOut])
def get_hotel_reviews(hotel_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    reviews = db.query(HotelReview).filter(HotelReview.hotel_id == hotel_id).order_by(HotelReview.id.desc()).all()
    return [
        HotelReviewOut(
            id=r.id,
            hotel_id=r.hotel_id,
            rating=r.rating,
            review_text=r.review_text,
            user_name=r.user.name if r.user else "Anonymous",
            created_at=r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for r in reviews
    ]


@router.post("/hotels/{hotel_id}/reviews", status_code=201)
def post_hotel_review(
    hotel_id: int,
    review_data: HotelReviewCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
        
    user_id = int(current_user["user_id"])
    
    # Save the review
    review = HotelReview(
        hotel_id=hotel_id,
        user_id=user_id,
        rating=review_data.rating,
        review_text=review_data.review_text
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Recalculate average rating & total reviews
    all_reviews = db.query(HotelReview).filter(HotelReview.hotel_id == hotel_id).all()
    total = len(all_reviews)
    avg = sum(r.rating for r in all_reviews) / total if total > 0 else 0.0
    
    hotel.avg_rating = round(avg, 1)
    hotel.total_reviews = total
    db.commit()
    
    return {"status": "success", "avg_rating": hotel.avg_rating, "total_reviews": hotel.total_reviews}


@router.post("/hotels/book", response_model=HotelBookingOut, status_code=201)
def book_hotel(
    data: HotelBookingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Lock the hotel row to prevent concurrent overbooking
    hotel = db.query(Hotel).filter(Hotel.id == data.hotel_id).with_for_update().first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    if hotel.rooms_available < data.num_rooms:
        raise HTTPException(status_code=400, detail="Not enough rooms available")

    try:
        d1 = date.fromisoformat(data.check_in_date)
        d2 = date.fromisoformat(data.check_out_date)
        if d2 <= d1:
            raise ValueError("Check-out date must be after check-in date.")
        nights = (d2 - d1).days
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date range: {str(e)}")

    total_price = hotel.price_per_night_inr * data.num_rooms * nights

    booking = HotelBooking(
        hotel_id=data.hotel_id,
        user_id=int(current_user["user_id"]),
        check_in_date=data.check_in_date,
        check_out_date=data.check_out_date,
        num_rooms=data.num_rooms,
        num_guests=data.num_guests,
        total_price_inr=total_price,
    )
    hotel.rooms_booked += data.num_rooms

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ── Trains ─────────────────────────────────────────────────────────────────

@router.post("/trains/search", response_model=list[TrainResult])
def search_trains(
    data: TrainSearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    escaped_origin = escape_like(data.origin)
    escaped_dest = escape_like(data.destination)
    trains = db.query(Train).filter(
        Train.origin.ilike(f"%{escaped_origin}%", escape='/'),
        Train.destination.ilike(f"%{escaped_dest}%", escape='/'),
    ).all()
    return [
        TrainResult(
            id=t.id, train_name=t.train_name, train_number=t.train_number,
            origin=t.origin, destination=t.destination,
            departure_time=t.departure_time, arrival_time=t.arrival_time,
            duration_hrs=t.duration_hrs, fare_inr=t.fare_inr,
            seats_available=t.seats_available, travel_class=t.travel_class,
        )
        for t in trains if t.seats_available >= data.num_seats
    ]


@router.post("/trains/book", response_model=TrainBookingOut, status_code=201)
def book_train(
    data: TrainBookingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    train = db.query(Train).filter(Train.id == data.train_id).with_for_update().first()
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    if train.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = train.fare_inr * data.num_seats

    booking = TrainBooking(
        train_id=data.train_id,
        user_id=int(current_user["user_id"]),
        passenger_name=data.passenger_name,
        travel_date=data.travel_date,
        num_seats=data.num_seats,
        total_fare_inr=total_fare,
    )
    train.seats_booked += data.num_seats

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ── Buses ──────────────────────────────────────────────────────────────────

@router.post("/buses/search", response_model=list[BusResult])
def search_buses(
    data: BusSearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    escaped_origin = escape_like(data.origin)
    escaped_dest = escape_like(data.destination)
    buses = db.query(Bus).filter(
        Bus.origin.ilike(f"%{escaped_origin}%", escape='/'),
        Bus.destination.ilike(f"%{escaped_dest}%", escape='/'),
    ).all()
    return [
        BusResult(
            id=b.id, operator_name=b.operator_name, bus_type=b.bus_type,
            origin=b.origin, destination=b.destination,
            departure_time=b.departure_time, arrival_time=b.arrival_time,
            duration_hrs=b.duration_hrs, fare_inr=b.fare_inr,
            seats_available=b.seats_available,
        )
        for b in buses if b.seats_available >= data.num_seats
    ]


@router.post("/buses/book", response_model=BusBookingOut, status_code=201)
def book_bus(
    data: BusBookingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    bus = db.query(Bus).filter(Bus.id == data.bus_id).with_for_update().first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    if bus.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = bus.fare_inr * data.num_seats

    booking = BusBooking(
        bus_id=data.bus_id,
        user_id=int(current_user["user_id"]),
        passenger_name=data.passenger_name,
        travel_date=data.travel_date,
        num_seats=data.num_seats,
        total_fare_inr=total_fare,
    )
    bus.seats_booked += data.num_seats

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ── Flights ────────────────────────────────────────────────────────────────

@router.post("/flights/search", response_model=list[FlightResult])
def search_flights(
    data: FlightSearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    escaped_origin = escape_like(data.origin)
    escaped_dest = escape_like(data.destination)
    flights = db.query(Flight).filter(
        Flight.origin.ilike(f"%{escaped_origin}%", escape='/'),
        Flight.destination.ilike(f"%{escaped_dest}%", escape='/'),
    ).all()
    return [
        FlightResult(
            id=f.id, airline=f.airline, flight_number=f.flight_number,
            origin=f.origin, destination=f.destination,
            departure_time=f.departure_time, arrival_time=f.arrival_time,
            duration_hrs=f.duration_hrs, fare_inr=f.fare_inr,
            seats_available=f.seats_available, travel_class=f.travel_class,
        )
        for f in flights if f.seats_available >= data.num_seats
    ]


@router.post("/flights/book", response_model=FlightBookingOut, status_code=201)
def book_flight(
    data: FlightBookingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    flight = db.query(Flight).filter(Flight.id == data.flight_id).with_for_update().first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if flight.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = flight.fare_inr * data.num_seats

    booking = FlightBooking(
        flight_id=data.flight_id,
        user_id=int(current_user["user_id"]),
        passenger_name=data.passenger_name,
        travel_date=data.travel_date,
        num_seats=data.num_seats,
        total_fare_inr=total_fare,
    )
    flight.seats_booked += data.num_seats

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
