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

from app.core.database import get_db
from app.models.models import Hotel, HotelBooking, Train, TrainBooking, Bus, BusBooking, Flight, FlightBooking
from app.schemas.booking_schemas import (
    HotelSearchRequest, HotelResult, HotelBookingRequest, HotelBookingOut,
    TrainSearchRequest, TrainResult, TrainBookingRequest, TrainBookingOut,
    BusSearchRequest, BusResult, BusBookingRequest, BusBookingOut,
    FlightSearchRequest, FlightResult, FlightBookingRequest, FlightBookingOut,
)

router = APIRouter()


# ── Hotels ─────────────────────────────────────────────────────────────────

@router.post("/hotels/search", response_model=list[HotelResult])
def search_hotels(data: HotelSearchRequest, db: Session = Depends(get_db)):
    hotels = db.query(Hotel).filter(Hotel.city.ilike(f"%{data.city}%")).all()
    return [
        HotelResult(
            id=h.id, name=h.name, city=h.city, address=h.address,
            star_rating=h.star_rating, price_per_night_inr=h.price_per_night_inr,
            rooms_available=h.rooms_available, amenities=h.amenities,
        )
        for h in hotels if h.rooms_available >= data.num_rooms
    ]


@router.post("/hotels/book", response_model=HotelBookingOut, status_code=201)
def book_hotel(data: HotelBookingRequest, db: Session = Depends(get_db)):
    hotel = db.query(Hotel).filter(Hotel.id == data.hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    if hotel.rooms_available < data.num_rooms:
        raise HTTPException(status_code=400, detail="Not enough rooms available")

    from datetime import date
    nights = 1
    try:
        d1 = date.fromisoformat(data.check_in_date)
        d2 = date.fromisoformat(data.check_out_date)
        nights = max((d2 - d1).days, 1)
    except Exception:
        pass

    total_price = hotel.price_per_night_inr * data.num_rooms * nights

    booking = HotelBooking(
        hotel_id=data.hotel_id,
        user_id=1,  # TODO: wire to get_current_user
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
def search_trains(data: TrainSearchRequest, db: Session = Depends(get_db)):
    trains = db.query(Train).filter(
        Train.origin.ilike(f"%{data.origin}%"),
        Train.destination.ilike(f"%{data.destination}%"),
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
def book_train(data: TrainBookingRequest, db: Session = Depends(get_db)):
    train = db.query(Train).filter(Train.id == data.train_id).first()
    if not train:
        raise HTTPException(status_code=404, detail="Train not found")
    if train.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = train.fare_inr * data.num_seats

    booking = TrainBooking(
        train_id=data.train_id,
        user_id=1,
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
def search_buses(data: BusSearchRequest, db: Session = Depends(get_db)):
    buses = db.query(Bus).filter(
        Bus.origin.ilike(f"%{data.origin}%"),
        Bus.destination.ilike(f"%{data.destination}%"),
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
def book_bus(data: BusBookingRequest, db: Session = Depends(get_db)):
    bus = db.query(Bus).filter(Bus.id == data.bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    if bus.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = bus.fare_inr * data.num_seats

    booking = BusBooking(
        bus_id=data.bus_id,
        user_id=1,
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
def search_flights(data: FlightSearchRequest, db: Session = Depends(get_db)):
    flights = db.query(Flight).filter(
        Flight.origin.ilike(f"%{data.origin}%"),
        Flight.destination.ilike(f"%{data.destination}%"),
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
def book_flight(data: FlightBookingRequest, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == data.flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if flight.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_fare = flight.fare_inr * data.num_seats

    booking = FlightBooking(
        flight_id=data.flight_id,
        user_id=1,
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
