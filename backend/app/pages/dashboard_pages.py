from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User, Trip, Vehicle
from app.core.auth import hash_password
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ---------------- USER FROM COOKIE ----------------

def get_user_from_cookie(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        return user
    except Exception:
        return None


def check_unread_bookings(user, db: Session) -> bool:
    if not user:
        return False
    from app.models.models import ProviderBooking
    return db.query(ProviderBooking).filter(
        ProviderBooking.user_id == user.id,
        ProviderBooking.message_unread == True
    ).count() > 0


# ---------------- DASHBOARD ----------------

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(Trip.created_at.desc()).limit(5).all()

    trip_count = db.query(Trip).filter(Trip.user_id == user.id).count()
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()

    has_unread_bookings = check_unread_bookings(user, db)
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "trips": trips,
        "trip_count": trip_count,
        "vehicle_count": len(vehicles),
        "has_unread_bookings": has_unread_bookings
    })


# ---------------- PLAN TRIP ----------------

@router.get("/plan-trip", response_class=HTMLResponse)
def plan_trip_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()
    token = request.cookies.get("access_token")

    has_unread_bookings = check_unread_bookings(user, db)
    return templates.TemplateResponse(request, "plan_trip.html", {
        "user": user,
        "vehicles": vehicles,
        "token": token,
        "has_unread_bookings": has_unread_bookings
    })


# ---------------- ADD VEHICLE ----------------

@router.get("/add-vehicle", response_class=HTMLResponse)
def add_vehicle_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()
    success = request.query_params.get("success")

    has_unread_bookings = check_unread_bookings(user, db)
    return templates.TemplateResponse(request, "add_vehicle.html", {
        "user": user,
        "vehicles": vehicles,
        "success": success,
        "has_unread_bookings": has_unread_bookings
    })


@router.post("/add-vehicle")
def add_vehicle_submit(
    request: Request,
    name: str = Form(...),
    fuel_type: str = Form(...),
    category: str = Form(...),
    mileage_kmpl: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicle = Vehicle(
        user_id=user.id,
        name=name,
        fuel_type=fuel_type,
        category=category,
        mileage_kmpl=mileage_kmpl
    )
    db.add(vehicle)
    db.commit()

    return RedirectResponse("/add-vehicle?success=Vehicle added successfully!", status_code=303)


@router.post("/delete-vehicle/{vehicle_id}")
def delete_vehicle(vehicle_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.user_id == user.id
    ).first()

    if vehicle:
        db.delete(vehicle)
        db.commit()

    return RedirectResponse("/add-vehicle?success=Vehicle deleted.", status_code=303)


# ---------------- MY TRIPS ----------------

@router.get("/my-trips", response_class=HTMLResponse)
def my_trips_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import TripStop

    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(Trip.created_at.desc()).all()

    for trip in trips:
        trip.stops = db.query(TripStop).filter(
            TripStop.trip_id == trip.id
        ).order_by(TripStop.day, TripStop.time_slot).all()

    has_unread_bookings = check_unread_bookings(user, db)
    return templates.TemplateResponse(request, "my_trips.html", {
        "user": user,
        "trips": trips,
        "has_unread_bookings": has_unread_bookings
    })


@router.post("/delete-trip/{trip_id}")
def delete_trip(trip_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import TripStop

    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id
    ).first()

    if trip:
        db.query(TripStop).filter(TripStop.trip_id == trip.id).delete()
        db.delete(trip)
        db.commit()

    return RedirectResponse("/my-trips", status_code=303)


# ---------------- TRIP ITINERARY & START TRIP ----------------

@router.get("/my-trips/{trip_id}/itinerary", response_class=HTMLResponse)
def trip_itinerary_page(trip_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import TripStop

    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id
    ).first()

    if not trip:
        return RedirectResponse("/my-trips", status_code=303)

    trip.stops = db.query(TripStop).filter(
        TripStop.trip_id == trip.id
    ).order_by(TripStop.day, TripStop.time_slot).all()

    from app.models.models import HotelBooking, Hotel, Booking, ProviderBooking
    booked_hotel = db.query(HotelBooking).join(Hotel).filter(
        HotelBooking.user_id == user.id,
        HotelBooking.status == "confirmed",
        Hotel.city.ilike(f"%{trip.destination}%"),
        HotelBooking.check_in_date == trip.start_date
    ).first()

    booked_hotel_dict = None
    if booked_hotel:
        booked_hotel_dict = {
            "hotel_name": booked_hotel.hotel.name,
            "check_in_date": booked_hotel.check_in_date,
            "check_out_date": booked_hotel.check_out_date,
            "num_rooms": booked_hotel.num_rooms
        }

    booked_bus = None
    booked_train = None
    booked_flight = None
    booked_cab = None

    from app.services.transport_service import get_transport_option_by_id

    # Transit bookings query
    transit_bookings = db.query(Booking).filter(
        Booking.user_id == user.id,
        Booking.travel_date == trip.start_date,
        Booking.status == "confirmed"
    ).all()

    for b in transit_bookings:
        opt = get_transport_option_by_id(b.transport_option_id, db)
        mode = opt.mode if opt else None
        operator = opt.operator if opt else None
        if not mode:
            try:
                mode = b.transport_option_id.split("_")[0]
            except:
                pass
        b_dict = {
            "id": str(b.id),
            "transport_option_id": b.transport_option_id,
            "passenger_name": b.passenger_name,
            "travel_date": b.travel_date,
            "include_return": b.include_return,
            "return_date": b.return_date,
            "going_fare_inr": b.going_fare_inr,
            "return_fare_inr": b.return_fare_inr,
            "total_fare_inr": b.total_fare_inr,
            "status": b.status,
            "selected_seats": b.selected_seats,
            "travel_class": b.travel_class,
            "mode": mode,
            "operator": operator,
            "departure_time": opt.departure_time if opt else "10:00 AM",
            "arrival_time": opt.arrival_time if opt else "06:00 PM",
        }
        if mode == "bus":
            booked_bus = b_dict
        elif mode == "train":
            booked_train = b_dict
        elif mode == "flight":
            booked_flight = b_dict

    # Cab bookings query
    cab_bookings = db.query(ProviderBooking).filter(
        ProviderBooking.user_id == user.id,
        ProviderBooking.travel_date == trip.start_date,
        ProviderBooking.status == "confirmed"
    ).all()

    for cb in cab_bookings:
        booked_cab = {
            "id": str(cb.id),
            "vehicle_id": cb.vehicle_id,
            "vehicle_name": cb.vehicle.vehicle_name if cb.vehicle else "Cab",
            "passenger_name": cb.passenger_name,
            "passenger_phone": cb.passenger_phone,
            "passenger_email": cb.passenger_email,
            "travel_date": cb.travel_date,
            "num_seats": cb.num_seats,
            "pickup_location": cb.pickup_location,
            "dropoff_location": cb.dropoff_location,
            "selected_seats": cb.selected_seats,
            "total_fare_inr": cb.total_fare_inr,
            "status": cb.status,
        }
        break

    token = request.cookies.get("access_token")
    has_unread_bookings = check_unread_bookings(user, db)
    
    return templates.TemplateResponse(request, "trip_itinerary.html", {
        "user": user,
        "trip": trip,
        "token": token,
        "has_unread_bookings": has_unread_bookings,
        "booked_hotel": booked_hotel_dict,
        "booked_bus": booked_bus,
        "booked_train": booked_train,
        "booked_flight": booked_flight,
        "booked_cab": booked_cab
    })


@router.get("/start-trip", response_class=HTMLResponse)
def start_trip_page(
    request: Request,
    trip_id: int = None,
    origin: str = "",
    destination: str = "",
    date: str = "",
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    trip = None
    if trip_id:
        trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user.id).first()
        if trip:
            if not origin:
                origin = trip.origin
            if not destination:
                destination = trip.destination
            if not date:
                date = trip.start_date

    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()
    token = request.cookies.get("access_token")
    has_unread_bookings = check_unread_bookings(user, db)

    booked_bus = None
    booked_train = None
    booked_flight = None
    booked_cab = None

    if date:
        from app.models.models import Booking, ProviderBooking
        from app.services.transport_service import get_transport_option_by_id

        transit_bookings = db.query(Booking).filter(
            Booking.user_id == user.id,
            Booking.travel_date == date,
            Booking.status == "confirmed"
        ).all()

        for b in transit_bookings:
            opt = get_transport_option_by_id(b.transport_option_id, db)
            mode = opt.mode if opt else None
            operator = opt.operator if opt else None
            if not mode:
                try:
                    mode = b.transport_option_id.split("_")[0]
                except:
                    pass
            b_dict = {
                "id": str(b.id),
                "transport_option_id": b.transport_option_id,
                "passenger_name": b.passenger_name,
                "travel_date": b.travel_date,
                "include_return": b.include_return,
                "return_date": b.return_date,
                "going_fare_inr": b.going_fare_inr,
                "return_fare_inr": b.return_fare_inr,
                "total_fare_inr": b.total_fare_inr,
                "status": b.status,
                "selected_seats": b.selected_seats,
                "travel_class": b.travel_class,
                "mode": mode,
                "operator": operator,
                "departure_time": opt.departure_time if opt else "10:00 AM",
                "arrival_time": opt.arrival_time if opt else "06:00 PM",
            }
            if mode == "bus":
                booked_bus = b_dict
            elif mode == "train":
                booked_train = b_dict
            elif mode == "flight":
                booked_flight = b_dict

        cab_bookings = db.query(ProviderBooking).filter(
            ProviderBooking.user_id == user.id,
            ProviderBooking.travel_date == date,
            ProviderBooking.status == "confirmed"
        ).all()

        for cb in cab_bookings:
            booked_cab = {
                "id": str(cb.id),
                "vehicle_id": cb.vehicle_id,
                "vehicle_name": cb.vehicle.vehicle_name if cb.vehicle else "Cab",
                "passenger_name": cb.passenger_name,
                "passenger_phone": cb.passenger_phone,
                "passenger_email": cb.passenger_email,
                "travel_date": cb.travel_date,
                "num_seats": cb.num_seats,
                "pickup_location": cb.pickup_location,
                "dropoff_location": cb.dropoff_location,
                "selected_seats": cb.selected_seats,
                "total_fare_inr": cb.total_fare_inr,
                "status": cb.status,
            }
            break

    return templates.TemplateResponse(request, "start_trip.html", {
        "user": user,
        "vehicles": vehicles,
        "token": token,
        "trip_id": trip_id,
        "trip": trip,
        "origin": origin,
        "destination": destination,
        "date": date,
        "has_unread_bookings": has_unread_bookings,
        "booked_bus": booked_bus,
        "booked_train": booked_train,
        "booked_flight": booked_flight,
        "booked_cab": booked_cab
    })


# ---------------- COMMUNITY ----------------

@router.get("/community", response_class=HTMLResponse)
async def community_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)

    try:
        from app.models.models import CommunityRoute
        routes = db.query(CommunityRoute).filter(
            CommunityRoute.is_public == True
        ).order_by(CommunityRoute.created_at.desc()).all()
    except Exception:
        db.rollback()
        routes = []

    token = request.cookies.get("access_token")
    has_unread_bookings = check_unread_bookings(user, db)

    return templates.TemplateResponse(request, "community.html", {
        "user": user,
        "routes": routes,
        "token": token,
        "has_unread_bookings": has_unread_bookings
    })
# ---------------- PROFILE ----------------

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import TripStop

    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(Trip.created_at.desc()).all()

    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()

    has_unread_bookings = check_unread_bookings(user, db)
    return templates.TemplateResponse(request, "profile.html", {
        "user": user,
        "trip_count": len(trips),
        "vehicle_count": len(vehicles),
        "has_unread_bookings": has_unread_bookings
    })


@router.post("/profile/update")
async def update_profile(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    if email != user.email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return RedirectResponse("/profile?error=Email already in use.", status_code=303)
        user.email = email

    user.name = name

    if password:
        user.password_hash = hash_password(password)

    db.commit()

    return RedirectResponse("/profile?success=Profile updated!", status_code=303)


# ---------------- MY BOOKINGS ----------------

@router.get("/my-bookings", response_class=HTMLResponse)
def my_bookings_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import ProviderBooking

    # Mark unread bookings for this user as read
    unread = db.query(ProviderBooking).filter(
        ProviderBooking.user_id == user.id,
        ProviderBooking.message_unread == True
    ).all()
    for b in unread:
        b.message_unread = False
    if unread:
        db.commit()

    cab_bookings = db.query(ProviderBooking).filter(
        ProviderBooking.user_id == user.id
    ).all()

    from app.models.models import Booking
    from app.services.transport_service import get_transport_option_by_id

    transit_bookings = db.query(Booking).filter(
        Booking.user_id == user.id
    ).all()

    for b in transit_bookings:
        opt = get_transport_option_by_id(b.transport_option_id, db)
        mode = None
        operator = None
        origin = None
        destination = None
        if opt:
            mode = opt.mode
            operator = opt.operator
            origin = opt.origin
            destination = opt.destination
        else:
            try:
                parts = b.transport_option_id.split("_")
                mode = parts[0]
            except Exception:
                pass
        b.mode = mode
        b.transport_option_operator = operator
        b.origin = origin
        b.destination = destination
        b.is_transit = True

    from app.models.models import HotelBooking
    hotel_bookings = db.query(HotelBooking).filter(
        HotelBooking.user_id == user.id
    ).all()

    for h in hotel_bookings:
        h.is_hotel = True
        h.hotel_name = h.hotel.name
        h.hotel_city = h.hotel.city
        h.hotel_address = h.hotel.address
        h.total_fare_inr = h.total_price_inr
        h.travel_date = h.check_in_date

    all_bookings = list(cab_bookings) + list(transit_bookings) + list(hotel_bookings)
    all_bookings.sort(key=lambda x: x.created_at, reverse=True)

    return templates.TemplateResponse(request, "my_bookings.html", {
        "user": user,
        "bookings": all_bookings,
        "has_unread_bookings": False
    })


@router.post("/cancel-booking/{booking_id}")
def cancel_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import ProviderBooking

    booking = db.query(ProviderBooking).filter(
        ProviderBooking.id == booking_id,
        ProviderBooking.user_id == user.id
    ).first()

    if booking and booking.status != "cancelled":
        booking.status = "cancelled"
        
        # Decrement the vehicle's booked seats count
        vehicle = booking.vehicle
        if vehicle:
            if vehicle.destination == "Private":
                vehicle.seats_booked = 0
            else:
                vehicle.seats_booked = max(vehicle.seats_booked - booking.num_seats, 0)
        
        db.commit()

    return RedirectResponse("/my-bookings", status_code=303)


@router.post("/cancel-transit-booking/{booking_id}")
def cancel_transit_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import Booking
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == user.id
    ).first()

    if booking and booking.status != "cancelled":
        booking.status = "cancelled"
        
        # Decrement seat count in the database
        try:
            parts = booking.transport_option_id.split("_")
            mode = parts[0]
            item_id = int(parts[1])
            if mode == "bus":
                from app.models.models import Bus
                bus = db.query(Bus).filter(Bus.id == item_id).first()
                if bus:
                    bus.seats_booked = max(bus.seats_booked - 1, 0)
            elif mode == "train":
                from app.models.models import Train
                train = db.query(Train).filter(Train.id == item_id).first()
                if train:
                    train.seats_booked = max(train.seats_booked - 1, 0)
            elif mode == "flight":
                from app.models.models import Flight
                flight = db.query(Flight).filter(Flight.id == item_id).first()
                if flight:
                    flight.seats_booked = max(flight.seats_booked - 1, 0)
        except Exception:
            pass
            
        db.commit()

    return RedirectResponse("/my-bookings", status_code=303)


@router.post("/cancel-hotel-booking/{booking_id}")
def cancel_hotel_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    from app.models.models import HotelBooking, Hotel
    booking = db.query(HotelBooking).filter(
        HotelBooking.id == booking_id,
        HotelBooking.user_id == user.id
    ).first()

    if booking and booking.status != "cancelled":
        booking.status = "cancelled"
        
        # Decrement rooms booked in the hotel
        hotel = db.query(Hotel).filter(Hotel.id == booking.hotel_id).first()
        if hotel:
            hotel.rooms_booked = max(hotel.rooms_booked - booking.num_rooms, 0)
            
        db.commit()

    return RedirectResponse("/my-bookings", status_code=303)