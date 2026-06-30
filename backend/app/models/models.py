from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey,Text
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
    origin_lat         = Column(Float, nullable=True)
    origin_lon         = Column(Float, nullable=True)
    destination_lat    = Column(Float, nullable=True)
    destination_lon    = Column(Float, nullable=True)
    start_date         = Column(String, nullable=False)
    end_date           = Column(String, nullable=True)
    budget_inr         = Column(Float,  nullable=False)
    travel_mode        = Column(String, nullable=False)
    group_type         = Column(String, nullable=True)
    num_people         = Column(Integer, default=1)
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
    selected_seats      = Column(String,  nullable=True)
    travel_class        = Column(String,  nullable=True)
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
    
# ── Hotels ─────────────────────────────────────────────────────────────────
 
class Hotel(Base):
    __tablename__ = "hotels"
 
    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    city          = Column(String, nullable=False, index=True)
    address       = Column(String, nullable=True)
    star_rating   = Column(Float, default=3.0)
    price_per_night_inr = Column(Float, nullable=False)
    total_rooms   = Column(Integer, default=10)
    rooms_booked  = Column(Integer, default=0)
    amenities     = Column(String, nullable=True)   # comma separated
    image_url     = Column(String, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())
 
    bookings = relationship("HotelBooking", back_populates="hotel")
 
    @property
    def rooms_available(self):
        return max(self.total_rooms - self.rooms_booked, 0)
 
 
class HotelBooking(Base):
    __tablename__ = "hotel_bookings"
 
    id            = Column(Integer, primary_key=True, index=True)
    hotel_id      = Column(Integer, ForeignKey("hotels.id"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in_date = Column(String, nullable=False)
    check_out_date= Column(String, nullable=False)
    num_rooms     = Column(Integer, default=1)
    num_guests    = Column(Integer, default=1)
    total_price_inr = Column(Float, nullable=False)
    status        = Column(String, default="confirmed")
    created_at    = Column(DateTime, server_default=func.now())
 
    hotel = relationship("Hotel", back_populates="bookings")
    user  = relationship("User")
 
 
# ── Trains ─────────────────────────────────────────────────────────────────
 
class Train(Base):
    __tablename__ = "trains"
 
    id              = Column(Integer, primary_key=True, index=True)
    train_name      = Column(String, nullable=False)
    train_number    = Column(String, nullable=False)
    origin          = Column(String, nullable=False, index=True)
    destination     = Column(String, nullable=False, index=True)
    departure_time  = Column(String, nullable=False)
    arrival_time    = Column(String, nullable=False)
    duration_hrs    = Column(Float, nullable=False)
    fare_inr        = Column(Float, nullable=False)
    total_seats     = Column(Integer, default=100)
    seats_booked    = Column(Integer, default=0)
    travel_class    = Column(String, default="Sleeper")  # Sleeper, AC3, AC2, AC1
    created_at      = Column(DateTime, server_default=func.now())
 
    bookings = relationship("TrainBooking", back_populates="train")
 
    @property
    def seats_available(self):
        return max(self.total_seats - self.seats_booked, 0)
 
 
class TrainBooking(Base):
    __tablename__ = "train_bookings"
 
    id              = Column(Integer, primary_key=True, index=True)
    train_id        = Column(Integer, ForeignKey("trains.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    passenger_name  = Column(String, nullable=False)
    travel_date     = Column(String, nullable=False)
    num_seats       = Column(Integer, default=1)
    total_fare_inr  = Column(Float, nullable=False)
    status          = Column(String, default="confirmed")
    created_at      = Column(DateTime, server_default=func.now())
 
    train = relationship("Train", back_populates="bookings")
    user  = relationship("User")
 
 
# ── Buses ──────────────────────────────────────────────────────────────────
 
class Bus(Base):
    __tablename__ = "buses"
 
    id              = Column(Integer, primary_key=True, index=True)
    operator_name   = Column(String, nullable=False)
    bus_type        = Column(String, default="AC Sleeper")  # AC Seater, AC Sleeper, Non-AC
    origin          = Column(String, nullable=False, index=True)
    destination     = Column(String, nullable=False, index=True)
    departure_time  = Column(String, nullable=False)
    arrival_time    = Column(String, nullable=False)
    duration_hrs    = Column(Float, nullable=False)
    fare_inr        = Column(Float, nullable=False)
    total_seats     = Column(Integer, default=40)
    seats_booked    = Column(Integer, default=0)
    created_at      = Column(DateTime, server_default=func.now())
 
    bookings = relationship("BusBooking", back_populates="bus")
 
    @property
    def seats_available(self):
        return max(self.total_seats - self.seats_booked, 0)
 
 
class BusBooking(Base):
    __tablename__ = "bus_bookings"
 
    id              = Column(Integer, primary_key=True, index=True)
    bus_id          = Column(Integer, ForeignKey("buses.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    passenger_name  = Column(String, nullable=False)
    travel_date     = Column(String, nullable=False)
    num_seats       = Column(Integer, default=1)
    total_fare_inr  = Column(Float, nullable=False)
    status          = Column(String, default="confirmed")
    created_at      = Column(DateTime, server_default=func.now())
 
    bus  = relationship("Bus", back_populates="bookings")
    user = relationship("User")
 
 
# ── Flights ────────────────────────────────────────────────────────────────
 
class Flight(Base):
    __tablename__ = "flights"
 
    id              = Column(Integer, primary_key=True, index=True)
    airline         = Column(String, nullable=False)
    flight_number   = Column(String, nullable=False)
    origin          = Column(String, nullable=False, index=True)
    destination     = Column(String, nullable=False, index=True)
    departure_time  = Column(String, nullable=False)
    arrival_time    = Column(String, nullable=False)
    duration_hrs    = Column(Float, nullable=False)
    fare_inr        = Column(Float, nullable=False)
    total_seats     = Column(Integer, default=180)
    seats_booked    = Column(Integer, default=0)
    travel_class    = Column(String, default="Economy")
    created_at      = Column(DateTime, server_default=func.now())
 
    bookings = relationship("FlightBooking", back_populates="flight")
 
    @property
    def seats_available(self):
        return max(self.total_seats - self.seats_booked, 0)
 
 
class FlightBooking(Base):
    __tablename__ = "flight_bookings"
 
    id              = Column(Integer, primary_key=True, index=True)
    flight_id       = Column(Integer, ForeignKey("flights.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    passenger_name  = Column(String, nullable=False)
    travel_date     = Column(String, nullable=False)
    num_seats       = Column(Integer, default=1)
    total_fare_inr  = Column(Float, nullable=False)
    status          = Column(String, default="confirmed")
    created_at      = Column(DateTime, server_default=func.now())
 
    flight = relationship("Flight", back_populates="bookings")
    user   = relationship("User")
 
 
# ── Travel Service Providers ──────────────────────────────────────────────
 
class Provider(Base):
    __tablename__ = "providers"

    id              = Column(Integer, primary_key=True, index=True)
    company_name    = Column(String, nullable=True)
    contact_person  = Column(String, nullable=True)
    email           = Column(String, unique=True, nullable=False, index=True)
    password_hash   = Column(String, nullable=False)
    phone           = Column(String, nullable=True)
    city            = Column(String, nullable=True)
    service_type    = Column(String, nullable=True)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime, server_default=func.now())
    alternate_email = Column(String, nullable=True)
    booking_mode    = Column(String, nullable=True)

    vehicles       = relationship("ProviderVehicle", back_populates="provider")
    vehicle_assets = relationship("ProviderVehicleAsset", back_populates="provider")


class ProviderVehicleAsset(Base):
    __tablename__ = "provider_vehicle_assets"

    id              = Column(Integer, primary_key=True, index=True)
    provider_id     = Column(Integer, ForeignKey("providers.id"), nullable=False)
    vehicle_type    = Column(String, nullable=False)   # sedan, suv, hatchback, mini_bus, traveller_bus, luxury_bus
    vehicle_name    = Column(String, nullable=False)   # e.g. "Volvo Multi-Axle", "Tempo Traveller"
    driver_included = Column(Boolean, default=True)
    total_seats     = Column(Integer, default=40)
    created_at      = Column(DateTime, server_default=func.now())

    provider = relationship("Provider", back_populates="vehicle_assets")


class ProviderVehicle(Base):
    __tablename__ = "provider_vehicles"
 
    id              = Column(Integer, primary_key=True, index=True)
    provider_id     = Column(Integer, ForeignKey("providers.id"), nullable=False)
    vehicle_asset_id = Column(Integer, ForeignKey("provider_vehicle_assets.id"), nullable=True)
    vehicle_type    = Column(String, nullable=False)   # sedan, suv, hatchback, mini_bus, traveller_bus
    vehicle_name    = Column(String, nullable=False)   # e.g. "Swift Dzire", "Tempo Traveller 12-seater"
    driver_included = Column(Boolean, default=True)
    origin          = Column(String, nullable=False, index=True)
    destination     = Column(String, nullable=False, index=True)
    departure_time  = Column(String, nullable=True)
    arrival_time    = Column(String, nullable=True)
    price_per_km_inr = Column(Float, nullable=True)
    fixed_fare_inr  = Column(Float, nullable=True)
    total_seats     = Column(Integer, default=4)
    seats_booked    = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    pickup_points   = Column(String, nullable=True)
    dropoff_points  = Column(String, nullable=True)
    service_dates   = Column(String, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())
 
    provider = relationship("Provider", back_populates="vehicles")
    bookings = relationship("ProviderBooking", back_populates="vehicle")
    vehicle_asset = relationship("ProviderVehicleAsset")
 
    @property
    def seats_available(self):
        return max(self.total_seats - self.seats_booked, 0)
 
 
class ProviderBooking(Base):
    __tablename__ = "provider_bookings"
 
    id              = Column(Integer, primary_key=True, index=True)
    vehicle_id      = Column(Integer, ForeignKey("provider_vehicles.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    passenger_name  = Column(String, nullable=False)
    passenger_phone = Column(String, nullable=True)
    passenger_email = Column(String, nullable=True)
    travel_date     = Column(String, nullable=False)
    num_seats       = Column(Integer, default=1)
    pickup_location = Column(String, nullable=True)
    dropoff_location = Column(String, nullable=True)
    selected_seats  = Column(String, nullable=True)
    total_fare_inr  = Column(Float, nullable=False)
    status          = Column(String, default="confirmed")
    navigation_status = Column(String, nullable=True)
    driver_lat      = Column(Float, nullable=True)
    driver_lon      = Column(Float, nullable=True)
    passenger_details = Column(String, nullable=True)
    message_unread  = Column(Boolean, default=False)
    provider_unread = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())
 
    vehicle = relationship("ProviderVehicle", back_populates="bookings")
    user    = relationship("User")
 
    @property
    def vehicle_name(self):
        return self.vehicle.vehicle_name if self.vehicle else "Vehicle"
 
    @property
    def passenger_details_parsed(self):
        if self.passenger_details:
            import json
            try:
                return json.loads(self.passenger_details)
            except Exception:
                pass
        return []


# ── Food & Restaurants ────────────────────────────────────────────────────────

class Restaurant(Base):
    __tablename__ = "restaurants"

    id              = Column(Integer, primary_key=True, index=True)
    provider_id     = Column(Integer, ForeignKey("providers.id"), nullable=True)
    name            = Column(String, nullable=False)
    city            = Column(String, nullable=False, index=True)
    address         = Column(String, nullable=False)
    rating          = Column(Float, default=4.0)
    reviews_count   = Column(Integer, default=0)
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)
    contact_number  = Column(String, nullable=True)
    image_url       = Column(String, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())

    menu_items = relationship("MenuItem", back_populates="restaurant", cascade="all, delete-orphan")
    orders = relationship("FoodOrder", back_populates="restaurant", cascade="all, delete-orphan")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id              = Column(Integer, primary_key=True, index=True)
    restaurant_id   = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name            = Column(String, nullable=False)
    description     = Column(String, nullable=True)
    price_inr       = Column(Float, nullable=False)
    category        = Column(String, default="Veg")  # Veg, Non-Veg, Egg, Beverage, Dessert
    rating          = Column(Float, default=4.0)
    created_at      = Column(DateTime, server_default=func.now())

    restaurant = relationship("Restaurant", back_populates="menu_items")
    reviews = relationship("FoodReview", back_populates="menu_item", cascade="all, delete-orphan")


class FoodOrder(Base):
    __tablename__ = "food_orders"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id   = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    items_json      = Column(String, nullable=False)  # JSON list of {menu_item_id, name, quantity, price}
    total_amount    = Column(Float, nullable=False)
    status          = Column(String, default="paid")  # paid, preparing, ready, completed
    preparation_time_mins = Column(Integer, default=20)  # Provider set time
    user_arrival_time_mins = Column(Integer, default=30)  # User arrival offset in minutes
    payment_method   = Column(String, default="prepaid")  # prepaid (wallet/card)
    created_at      = Column(DateTime, server_default=func.now())

    restaurant = relationship("Restaurant", back_populates="orders")
    user = relationship("User")


class FoodReview(Base):
    __tablename__ = "food_reviews"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    menu_item_id    = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    rating          = Column(Integer, default=5)  # 1 to 5 stars
    comment         = Column(String, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())

    menu_item = relationship("MenuItem", back_populates="reviews")
    user = relationship("User")