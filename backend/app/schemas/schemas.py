from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class FuelType(str, Enum):
    petrol  = "petrol"
    diesel  = "diesel"
    cng     = "cng"
    electric = "electric"

class VehicleCategory(str, Enum):
    two_wheeler = "two_wheeler"
    car         = "car"
    suv         = "suv"
    van         = "van"

class GroupType(str, Enum):
    solo   = "solo"
    couple = "couple"
    family = "family"
    friends = "friends"


# ─── User / Auth ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    home_city: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    home_city: Optional[str]
    total_trips: int = 0

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Vehicle ──────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    name: str                              # e.g. "My Swift"
    fuel_type: FuelType
    category: VehicleCategory
    mileage_kmpl: float                    # km/L or km/kWh for EVs
    tank_capacity_litres: Optional[float] = None
    ev_range_km: Optional[float] = None   # only for electric

class VehicleOut(VehicleCreate):
    id: str
    user_id: str


# ─── Trip Planner ─────────────────────────────────────────────────────────────

class TripCreate(BaseModel):
    origin: str                            # e.g. "Jaipur, Rajasthan"
    destination: str                       # e.g. "Udaipur, Rajasthan"
    start_date: str                        # "2025-12-01"
    end_date: str                          # "2025-12-03"
    budget_inr: float
    vehicle_id: str
    group_type: GroupType
    num_people: int = 1

class ItineraryStop(BaseModel):
    day: int
    time_slot: str                         # "morning" / "afternoon" / "evening"
    place_name: str
    place_type: str                        # "viewpoint" / "hotel" / "dhaba" / "fuel"
    description: str
    estimated_cost_inr: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class TripOut(BaseModel):
    id: str
    origin: str
    destination: str
    total_distance_km: float
    stops: List[ItineraryStop]
    total_estimated_cost_inr: float
    ai_summary: str


# ─── Fuel & Toll ──────────────────────────────────────────────────────────────

class FuelCalcRequest(BaseModel):
    origin: str
    destination: str
    vehicle_id: str
    include_return: bool = False

class FuelCalcOut(BaseModel):
    distance_km: float
    fuel_litres_required: float
    fuel_cost_inr: float
    toll_cost_inr: float
    total_one_way_inr: float
    total_with_return_inr: Optional[float] = None
    fuel_price_per_litre: float
    city: str


# ─── Community Routes ─────────────────────────────────────────────────────────

class RoutePost(BaseModel):
    trip_id: str
    title: str
    description: str
    tags: List[str] = []               # ["scenic", "family-friendly", "EV-safe"]
    is_public: bool = True

class RouteReview(BaseModel):
    route_id: str
    rating: int                        # 1–5
    review_text: str
    tags: List[str] = []

class RouteOut(BaseModel):
    id: str
    title: str
    origin: str
    destination: str
    description: str
    tags: List[str]
    avg_rating: float
    total_reviews: int
    clone_count: int
    author_name: str


# ─── Trip Journal ─────────────────────────────────────────────────────────────

class JournalEntryCreate(BaseModel):
    trip_id: str
    stop_name: str
    notes: Optional[str] = None
    expense_inr: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class JournalOut(BaseModel):
    id: str
    trip_id: str
    entries: list
    total_expense_inr: float
    is_public: bool
