"""
Provider Schemas — RoadBuddy
------------------------------
Pydantic models for the Travel Service Provider interface.
Save as: app/provider/schemas.py
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class ServiceType(str, Enum):
    car_rental = "car_rental"
    bus_operator = "bus_operator"
    both = "both"


class VehicleType(str, Enum):
    sedan = "sedan"
    suv = "suv"
    hatchback = "hatchback"
    muv = "muv"
    mini_bus = "mini_bus"
    traveller_bus = "traveller_bus"
    luxury_bus = "luxury_bus"


# ── Provider Auth ──────────────────────────────────────────────────────────

class ProviderRegister(BaseModel):
    company_name: str
    contact_person: str
    email: EmailStr
    password: str
    phone: str
    city: str
    service_type: ServiceType


class ProviderLogin(BaseModel):
    email: EmailStr
    password: str


class ProviderOut(BaseModel):
    id: int
    company_name: str
    contact_person: str
    email: str
    phone: str
    city: str
    service_type: str
    is_verified: bool

    class Config:
        from_attributes = True


# ── Vehicle Management ────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    vehicle_type: VehicleType
    vehicle_name: str
    driver_included: bool = True
    origin: str
    destination: str
    departure_time: Optional[str] = None
    price_per_km_inr: Optional[float] = None
    fixed_fare_inr: Optional[float] = None
    total_seats: int = 4


class VehicleUpdate(BaseModel):
    vehicle_name: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_time: Optional[str] = None
    price_per_km_inr: Optional[float] = None
    fixed_fare_inr: Optional[float] = None
    total_seats: Optional[int] = None
    is_active: Optional[bool] = None


class VehicleOut(BaseModel):
    id: int
    provider_id: int
    vehicle_type: str
    vehicle_name: str
    driver_included: bool
    origin: str
    destination: str
    departure_time: Optional[str]
    price_per_km_inr: Optional[float]
    fixed_fare_inr: Optional[float]
    total_seats: int
    seats_booked: int
    seats_available: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Search (for user-facing search) ───────────────────────────────────────

class VehicleSearchRequest(BaseModel):
    origin: str
    destination: str
    travel_date: Optional[str] = None
    num_seats: int = 1


class VehicleSearchResult(BaseModel):
    id: int
    provider_name: str
    vehicle_type: str
    vehicle_name: str
    driver_included: bool
    origin: str
    destination: str
    departure_time: Optional[str]
    estimated_fare_inr: float
    seats_available: int


# ── Cab Services (all providers, no route filter) ────────────────────────

class CabServiceResult(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    cab_category: str          # "private" | "company" | "rental"
    vehicle_type: str
    vehicle_name: str
    driver_included: bool
    origin: str
    destination: str
    departure_time: Optional[str]
    price_per_km_inr: Optional[float]
    fixed_fare_inr: Optional[float]
    total_seats: int
    seats_available: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Booking ────────────────────────────────────────────────────────────────

class ProviderBookingCreate(BaseModel):
    vehicle_id: int
    passenger_name: str
    travel_date: str
    num_seats: int = 1
    pickup_location: Optional[str] = None


class ProviderBookingOut(BaseModel):
    id: int
    vehicle_id: int
    passenger_name: str
    travel_date: str
    num_seats: int
    total_fare_inr: float
    status: str

    class Config:
        from_attributes = True
