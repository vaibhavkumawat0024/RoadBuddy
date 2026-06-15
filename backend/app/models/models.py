from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at    = Column(DateTime, server_default=func.now())

    vehicles = relationship("Vehicle", back_populates="owner")
    trips    = relationship("Trip",    back_populates="user")


# ── Vehicles ──────────────────────────────────────────────────────────────────

class Vehicle(Base):
    __tablename__ = "vehicles"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    name         = Column(String, nullable=False)
    fuel_type    = Column(String, nullable=False)
    category     = Column(String, nullable=False)
    mileage_kmpl = Column(Float, nullable=False)

    owner = relationship("User",  back_populates="vehicles")
    trips = relationship("Trip",  back_populates="vehicle")


# ── Trips ─────────────────────────────────────────────────────────────────────

class Trip(Base):
    __tablename__ = "trips"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, ForeignKey("users.id"),    nullable=False)
    vehicle_id         = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    origin             = Column(String, nullable=False)
    destination        = Column(String, nullable=False)
    start_date         = Column(String, nullable=False)
    budget_inr         = Column(Float,  nullable=False)
    travel_mode        = Column(String, nullable=False)
    fuel_cost_inr      = Column(Float, default=0)
    toll_cost_inr      = Column(Float, default=0)
    transport_fare_inr = Column(Float, default=0)
    return_fare_inr    = Column(Float, default=0)
    hotel_cost_inr     = Column(Float, default=0)
    food_cost_inr      = Column(Float, default=0)
    total_cost_inr     = Column(Float, default=0)
    ai_summary         = Column(String, nullable=True)
    created_at         = Column(DateTime, server_default=func.now())

    user    = relationship("User",    back_populates="trips")
    vehicle = relationship("Vehicle", back_populates="trips")
    stops   = relationship("TripStop", back_populates="trip")


# ── Trip Stops ────────────────────────────────────────────────────────────────

class TripStop(Base):
    __tablename__ = "trip_stops"

    id         = Column(Integer, primary_key=True, index=True)
    trip_id    = Column(Integer, ForeignKey("trips.id"), nullable=False)
    day        = Column(Integer, nullable=False)
    time_slot  = Column(String,  nullable=False)
    place_name = Column(String,  nullable=False)
    place_type = Column(String,  nullable=False)

    trip = relationship("Trip", back_populates="stops")


# ── Transport Options ─────────────────────────────────────────────────────────

class TransportOption(Base):
    __tablename__ = "transport_options"

    id              = Column(Integer, primary_key=True, index=True)
    origin          = Column(String, nullable=False)
    destination     = Column(String, nullable=False)
    mode            = Column(String, nullable=False)
    operator        = Column(String, nullable=False)
    departure_time  = Column(String, nullable=False)
    arrival_time    = Column(String, nullable=False)
    duration_hrs    = Column(Float,  nullable=False)
    fare_inr        = Column(Float,  nullable=False)
    seats_available = Column(Integer, nullable=False)


# ── Bookings ──────────────────────────────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False)
    transport_option_id = Column(String,  nullable=False)
    passenger_name      = Column(String,  nullable=False)
    travel_date         = Column(String,  nullable=False)
    include_return      = Column(Boolean, default=False)
    return_date         = Column(String,  nullable=True)
    going_fare_inr      = Column(Float,   nullable=False)
    return_fare_inr     = Column(Float,   default=0)
    total_fare_inr      = Column(Float,   nullable=False)
    status              = Column(String,  default="confirmed")
    created_at          = Column(DateTime, server_default=func.now())

    user = relationship("User")

# ── Community Routes ──────────────────────────────────────────────────────────

class CommunityRoute(Base):
    __tablename__ = "community_routes"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    trip_id     = Column(String,  nullable=False)
    title       = Column(String,  nullable=False)
    description = Column(String,  nullable=False)
    tags        = Column(String,  nullable=True)   # stored as comma separated
    is_public   = Column(Boolean, default=True)
    origin      = Column(String,  default="Unknown")
    destination = Column(String,  default="Unknown")
    avg_rating  = Column(Float,   default=0.0)
    total_reviews = Column(Integer, default=0)
    clone_count = Column(Integer, default=0)
    created_at  = Column(DateTime, server_default=func.now())

    user    = relationship("User")
    reviews = relationship("RouteReview", back_populates="route")


# ── Route Reviews ─────────────────────────────────────────────────────────────

class RouteReview(Base):
    __tablename__ = "route_reviews"

    id          = Column(Integer, primary_key=True, index=True)
    route_id    = Column(Integer, ForeignKey("community_routes.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating      = Column(Integer, nullable=False)
    review_text = Column(String,  nullable=False)
    tags        = Column(String,  nullable=True)
    created_at  = Column(DateTime, server_default=func.now())

    route = relationship("CommunityRoute", back_populates="reviews")
    user  = relationship("User")

# ── Journal ───────────────────────────────────────────────────────────────────

class Journal(Base):
    __tablename__ = "journals"

    id                = Column(Integer, primary_key=True, index=True)
    trip_id           = Column(String,  nullable=False, unique=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_expense_inr = Column(Float,   default=0.0)
    is_public         = Column(Boolean, default=False)
    created_at        = Column(DateTime, server_default=func.now())

    user    = relationship("User")
    entries = relationship("JournalEntry", back_populates="journal")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id         = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False)
    stop_name  = Column(String,  nullable=False)
    notes      = Column(String,  nullable=True)
    expense_inr = Column(Float,  default=0.0)
    lat        = Column(Float,   nullable=True)
    lng        = Column(Float,   nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    journal = relationship("Journal", back_populates="entries")