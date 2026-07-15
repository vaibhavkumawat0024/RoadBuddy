"""
Travel Booking Schemas — RoadBuddy
-------------------------------------
Pydantic models for hotels, trains, buses, flights search & booking.
Save as: app/schemas/booking_schemas.py
"""

from pydantic import BaseModel
from typing import Optional


# ── Hotels ─────────────────────────────────────────────────────────────────

class HotelSearchRequest(BaseModel):
    city: str
    check_in_date: Optional[str] = None
    check_out_date: Optional[str] = None
    num_rooms: int = 1


class HotelResult(BaseModel):
    id: int
    name: str
    city: str
    address: Optional[str]
    star_rating: float
    price_per_night_inr: float
    rooms_available: int
    amenities: Optional[str]
    avg_rating: Optional[float] = 0.0
    total_reviews: Optional[int] = 0

    class Config:
        from_attributes = True


class HotelReviewCreate(BaseModel):
    rating: int
    review_text: str


class HotelReviewOut(BaseModel):
    id: int
    hotel_id: int
    rating: int
    review_text: str
    user_name: str
    created_at: str

    class Config:
        from_attributes = True


class HotelBookingRequest(BaseModel):
    hotel_id: int
    check_in_date: str
    check_out_date: str
    num_rooms: int = 1
    num_guests: int = 1


class HotelBookingOut(BaseModel):
    id: int
    hotel_id: int
    check_in_date: str
    check_out_date: str
    num_rooms: int
    num_guests: int
    total_price_inr: float
    status: str

    class Config:
        from_attributes = True


# ── Trains ─────────────────────────────────────────────────────────────────

class TrainSearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: Optional[str] = None
    num_seats: int = 1


class TrainResult(BaseModel):
    id: int
    train_name: str
    train_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_hrs: float
    fare_inr: float
    seats_available: int
    travel_class: str

    class Config:
        from_attributes = True


class TrainBookingRequest(BaseModel):
    train_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


class TrainBookingOut(BaseModel):
    id: int
    train_id: int
    passenger_name: str
    travel_date: str
    num_seats: int
    total_fare_inr: float
    status: str

    class Config:
        from_attributes = True


# ── Buses ──────────────────────────────────────────────────────────────────

class BusSearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: Optional[str] = None
    num_seats: int = 1


class BusResult(BaseModel):
    id: int
    operator_name: str
    bus_type: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_hrs: float
    fare_inr: float
    seats_available: int

    class Config:
        from_attributes = True


class BusBookingRequest(BaseModel):
    bus_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


class BusBookingOut(BaseModel):
    id: int
    bus_id: int
    passenger_name: str
    travel_date: str
    num_seats: int
    total_fare_inr: float
    status: str

    class Config:
        from_attributes = True


# ── Flights ────────────────────────────────────────────────────────────────

class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: Optional[str] = None
    num_seats: int = 1


class FlightResult(BaseModel):
    id: int
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_hrs: float
    fare_inr: float
    seats_available: int
    travel_class: str

    class Config:
        from_attributes = True


class FlightBookingRequest(BaseModel):
    flight_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1


class FlightBookingOut(BaseModel):
    id: int
    flight_id: int
    passenger_name: str
    travel_date: str
    num_seats: int
    total_fare_inr: float
    status: str

    class Config:
        from_attributes = True
