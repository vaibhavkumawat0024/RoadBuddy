"""
Provider API Router — RoadBuddy
----------------------------------
REST endpoints for provider registration, login, and vehicle management.
Save as: app/provider/router.py
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Provider, ProviderVehicle, ProviderBooking, User, ProviderVehicleAsset
from app.provider.schemas import (
    ProviderRegister, ProviderLogin, ProviderOut,
    VehicleCreate, VehicleUpdate, VehicleOut,
    VehicleSearchRequest, VehicleSearchResult,
    ProviderBookingCreate, ProviderBookingOut,
    CabServiceResult,
    VehicleAssetCreate, VehicleAssetOut,
)
from app.provider.auth import (
    hash_password, verify_password,
    create_provider_token, get_current_provider,
)
from app.core.auth import get_current_user

router = APIRouter()


# ── Auth ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=ProviderOut, status_code=201)
def register_provider(data: ProviderRegister, db: Session = Depends(get_db)):
    existing = db.query(Provider).filter(Provider.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    provider = Provider(
        company_name=data.company_name,
        contact_person=data.contact_person,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        city=data.city,
        service_type=data.service_type,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.post("/login")
def login_provider(data: ProviderLogin, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.email == data.email).first()
    if not provider or not verify_password(data.password, provider.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_provider_token(provider.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "provider": ProviderOut.from_orm(provider),
    }


@router.get("/me", response_model=ProviderOut)
def get_me(provider: Provider = Depends(get_current_provider)):
    return provider


# ── Vehicle Asset Management ──────────────────────────────────────────────

@router.post("/vehicle-assets", response_model=VehicleAssetOut, status_code=201)
def add_vehicle_asset(
    data: VehicleAssetCreate,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    asset = ProviderVehicleAsset(
        provider_id=provider.id,
        vehicle_type=data.vehicle_type,
        vehicle_name=data.vehicle_name,
        driver_included=data.driver_included,
        total_seats=data.total_seats,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/vehicle-assets", response_model=list[VehicleAssetOut])
def list_my_vehicle_assets(
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    assets = db.query(ProviderVehicleAsset).filter(
        ProviderVehicleAsset.provider_id == provider.id
    ).all()
    return assets


@router.delete("/vehicle-assets/{asset_id}", status_code=204)
def delete_vehicle_asset(
    asset_id: int,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    asset = db.query(ProviderVehicleAsset).filter(
        ProviderVehicleAsset.id == asset_id,
        ProviderVehicleAsset.provider_id == provider.id,
    ).first()
    if asset:
        db.query(ProviderVehicle).filter(
            ProviderVehicle.vehicle_asset_id == asset_id
        ).update({ProviderVehicle.vehicle_asset_id: None})
        db.delete(asset)
        db.commit()


# ── Vehicle Management ────────────────────────────────────────────────────

@router.post("/vehicles", response_model=VehicleOut, status_code=201)
def add_vehicle(
    data: VehicleCreate,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    v_type = data.vehicle_type
    v_name = data.vehicle_name
    v_driver = data.driver_included
    v_seats = data.total_seats

    if data.vehicle_asset_id:
        asset = db.query(ProviderVehicleAsset).filter(
            ProviderVehicleAsset.id == data.vehicle_asset_id,
            ProviderVehicleAsset.provider_id == provider.id
        ).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Vehicle asset not found")
        v_type = asset.vehicle_type
        v_name = asset.vehicle_name
        v_driver = asset.driver_included
        v_seats = asset.total_seats

    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_asset_id=data.vehicle_asset_id,
        vehicle_type=v_type,
        vehicle_name=v_name,
        driver_included=v_driver,
        origin=data.origin,
        destination=data.destination,
        departure_time=data.departure_time,
        price_per_km_inr=data.price_per_km_inr,
        fixed_fare_inr=data.fixed_fare_inr,
        total_seats=v_seats,
        pickup_points=data.pickup_points,
        dropoff_points=data.dropoff_points,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return _to_vehicle_out(vehicle)


@router.get("/vehicles", response_model=list[VehicleOut])
def list_my_vehicles(
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()
    return [_to_vehicle_out(v) for v in vehicles]


@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    vehicle = db.query(ProviderVehicle).filter(
        ProviderVehicle.id == vehicle_id,
        ProviderVehicle.provider_id == provider.id,
    ).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return _to_vehicle_out(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(
    vehicle_id: int,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    vehicle = db.query(ProviderVehicle).filter(
        ProviderVehicle.id == vehicle_id,
        ProviderVehicle.provider_id == provider.id,
    ).first()
    if vehicle:
        db.delete(vehicle)
        db.commit()


@router.get("/bookings", response_model=list[ProviderBookingOut])
def list_my_bookings(
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    vehicle_ids = [v.id for v in db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()]
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id.in_(vehicle_ids)
    ).order_by(ProviderBooking.created_at.desc()).all()
    return bookings


# ── Public Search (called from USER side) ────────────────────────────────

def _derive_cab_category(provider: Provider, vehicle: ProviderVehicle) -> str:
    """
    Classify a listed vehicle as private / company / rental for the
    user-facing Cab Service tab.

    Real signals (from provider_dashboard.html setup form + provider_vehicles.html):
      - Provider.service_type: car_rental | bus_traveller_rental | both_car_big | self_drive
      - ProviderVehicle.destination == "Private" sentinel -> listed via the
        "Private Booking Service" form (distance-based, price_per_km_inr)
      - Anything else -> listed via the "Route-Based Public Service" form
        (fixed origin->destination, schedule, fixed_fare_inr)
    """
    service_type = (provider.service_type or "").lower()

    if "self_drive" in service_type:
        return "rental"

    if vehicle.destination == "Private":
        return "private"

    if service_type in ("bus_traveller_rental", "both_car_big"):
        return "company"

    # car_rental provider running a scheduled route is still an operator-style listing
    return "company"


@router.get("/services", response_model=list[CabServiceResult])
def list_cab_services(
    cab_category: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    List ALL active provider vehicles (private cabs, company/bus operators,
    rentals) for the user-facing 'Cab Service' tab. No exact route match
    required — origin/destination are optional loose filters.
    Public — no auth needed.
    """
    query = db.query(ProviderVehicle).filter(ProviderVehicle.is_active == True)
    if origin:
        from sqlalchemy import func
        query = query.filter(
            (ProviderVehicle.origin.ilike(f"%{origin}%")) |
            (func.lower(origin).like(func.concat("%", func.lower(ProviderVehicle.origin), "%")))
        )
    if destination:
        # "Private" vehicles have no real destination (they're priced per-km,
        # available from a city, not tied to a fixed route) — don't exclude
        # them just because the user typed a destination for route-based search.
        from sqlalchemy import func
        query = query.filter(
            (ProviderVehicle.destination.ilike(f"%{destination}%")) |
            (func.lower(destination).like(func.concat("%", func.lower(ProviderVehicle.destination), "%"))) |
            (ProviderVehicle.destination == "Private")
        )

    results = []
    for v in query.all():
        provider = db.query(Provider).filter(Provider.id == v.provider_id).first()
        if not provider:
            continue
        category = _derive_cab_category(provider, v)
        if cab_category and cab_category.lower() != category:
            continue

        # Private cab visibility logic:
        if v.destination == "Private":
            # Check if this private vehicle has any active bookings
            booking = db.query(ProviderBooking).filter(
                ProviderBooking.vehicle_id == v.id,
                ProviderBooking.status != "cancelled"
            ).first()
            if booking:
                # If booked, only show if it belongs to the requesting user_id
                if user_id is None or booking.user_id != user_id:
                    continue

        results.append(CabServiceResult(
            id=v.id,
            provider_id=provider.id,
            provider_name=provider.company_name or "Unknown",
            cab_category=category,
            vehicle_type=v.vehicle_type,
            vehicle_name=v.vehicle_name,
            driver_included=v.driver_included,
            origin=v.origin,
            destination=v.destination,
            departure_time=v.departure_time,
            price_per_km_inr=v.price_per_km_inr,
            fixed_fare_inr=v.fixed_fare_inr,
            total_seats=v.total_seats,
            seats_available=v.seats_available,
            is_active=v.is_active,
            pickup_points=v.pickup_points,
            dropoff_points=v.dropoff_points,
        ))
    return results


@router.post("/search", response_model=list[VehicleSearchResult])
def search_vehicles(data: VehicleSearchRequest, db: Session = Depends(get_db)):
    """Search available provider vehicles for a route. Public — no auth needed."""
    from sqlalchemy import func
    vehicles = db.query(ProviderVehicle).filter(
        ((ProviderVehicle.origin.ilike(f"%{data.origin}%")) |
         (func.lower(data.origin).like(func.concat("%", func.lower(ProviderVehicle.origin), "%")))),
        ((ProviderVehicle.destination.ilike(f"%{data.destination}%")) |
         (func.lower(data.destination).like(func.concat("%", func.lower(ProviderVehicle.destination), "%")))),
        ProviderVehicle.is_active == True,
    ).all()

    results = []
    for v in vehicles:
        if v.seats_available < data.num_seats:
            continue
        provider = db.query(Provider).filter(Provider.id == v.provider_id).first()
        fare = v.fixed_fare_inr if v.fixed_fare_inr else (v.price_per_km_inr or 0) * 100  # rough estimate
        results.append(VehicleSearchResult(
            id=v.id,
            provider_name=provider.company_name if provider else "Unknown",
            vehicle_type=v.vehicle_type,
            vehicle_name=v.vehicle_name,
            driver_included=v.driver_included,
            origin=v.origin,
            destination=v.destination,
            departure_time=v.departure_time,
            estimated_fare_inr=fare,
            seats_available=v.seats_available,
        ))
    return results


# ── Booking (called from USER side, needs user auth not provider auth) ──

def _calculate_geodesic_distance(p1_str: str, p2_str: str) -> float:
    import math
    def extract_lat_lon(loc_str):
        if not loc_str or "|||" not in loc_str:
            return None
        try:
            coord_part = loc_str.split("|||")[1]
            lat_str, lon_str = coord_part.split(",")
            return float(lat_str), float(lon_str)
        except Exception:
            return None

    c1 = extract_lat_lon(p1_str)
    c2 = extract_lat_lon(p2_str)
    if not c1 or not c2:
        return 100.0  # fallback default distance in km

    lat1, lon1 = c1
    lat2, lon2 = c2

    # Haversine formula
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@router.post("/book", response_model=ProviderBookingOut, status_code=201)
def book_vehicle(
    data: ProviderBookingCreate,
    db: Session = Depends(get_db),
):
    """Book a provider vehicle. In production wire this to get_current_user (the rider)."""
    vehicle = db.query(ProviderVehicle).filter(ProviderVehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if vehicle.seats_available < data.num_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    if vehicle.destination == "Private":
        # Private cab: fare = distance * price_per_km * total_seats
        dist = _calculate_geodesic_distance(data.pickup_location, data.dropoff_location)
        fare_per_km = vehicle.price_per_km_inr or 0.0
        total_fare = dist * fare_per_km * (vehicle.total_seats or 4)
        total_fare = round(total_fare, 2)
    else:
        # Route-based cab: fare = fixed_fare * num_seats
        fare = vehicle.fixed_fare_inr if vehicle.fixed_fare_inr else (vehicle.price_per_km_inr or 0) * 100
        total_fare = fare * data.num_seats

    # NOTE: user_id hardcoded to 1 here as placeholder — wire to get_current_user in trips router
    booking = ProviderBooking(
        vehicle_id=data.vehicle_id,
        user_id=data.user_id if data.user_id else 1,
        passenger_name=data.passenger_name,
        passenger_phone=data.passenger_phone,
        passenger_email=data.passenger_email,
        travel_date=data.travel_date,
        num_seats=data.num_seats,
        pickup_location=data.pickup_location,
        dropoff_location=data.dropoff_location,
        selected_seats=data.selected_seats,
        total_fare_inr=total_fare,
    )
    
    if vehicle.destination == "Private":
        vehicle.seats_booked = vehicle.total_seats
    else:
        vehicle.seats_booked += data.num_seats

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/vehicles/{vehicle_id}/booked-seats")
def get_booked_seats(
    vehicle_id: int,
    travel_date: str,
    db: Session = Depends(get_db),
):
    """
    Get a list of already booked seat numbers for a vehicle on a specific travel date.
    """
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id == vehicle_id,
        ProviderBooking.travel_date == travel_date,
        ProviderBooking.status != "cancelled"
    ).all()
    
    booked_seats = []
    for b in bookings:
        if b.selected_seats:
            seats = [s.strip() for s in b.selected_seats.split(",") if s.strip()]
            booked_seats.extend(seats)
            
    return {"booked_seats": list(set(booked_seats))}


def _to_vehicle_out(v: ProviderVehicle) -> VehicleOut:
    return VehicleOut(
        id=v.id,
        provider_id=v.provider_id,
        vehicle_type=v.vehicle_type,
        vehicle_name=v.vehicle_name,
        driver_included=v.driver_included,
        origin=v.origin,
        destination=v.destination,
        departure_time=v.departure_time,
        price_per_km_inr=v.price_per_km_inr,
        fixed_fare_inr=v.fixed_fare_inr,
        total_seats=v.total_seats,
        seats_booked=v.seats_booked,
        seats_available=v.seats_available,
        is_active=v.is_active,
        pickup_points=v.pickup_points,
        dropoff_points=v.dropoff_points,
        vehicle_asset_id=v.vehicle_asset_id,
    )


# ── LIVE DRIVER GEOLOCATION TRACKING ENDPOINTS ──

from pydantic import BaseModel

class LocationUpdateSchema(BaseModel):
    lat: float
    lon: float

@router.post("/bookings/{booking_id}/start-nav")
def start_booking_navigation(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(ProviderBooking).filter(ProviderBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.navigation_status = "enroute"
    booking.message_unread = True
    db.commit()
    return {"status": "success"}

@router.post("/bookings/{booking_id}/location")
def update_booking_location(booking_id: int, data: LocationUpdateSchema, db: Session = Depends(get_db)):
    booking = db.query(ProviderBooking).filter(ProviderBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.driver_lat = data.lat
    booking.driver_lon = data.lon
    db.commit()
    return {"status": "success"}

@router.get("/bookings/{booking_id}/track")
def track_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(ProviderBooking).filter(ProviderBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Parse coordinates if present
    def parse_coords(loc_str):
        if loc_str and "|||" in loc_str:
            try:
                coords = loc_str.split("|||")[1].split(",")
                return float(coords[0]), float(coords[1])
            except Exception:
                pass
        return None, None

    p_lat, p_lon = parse_coords(booking.pickup_location)
    d_lat, d_lon = parse_coords(booking.dropoff_location)

    return {
        "id": booking.id,
        "status": booking.status,
        "navigation_status": booking.navigation_status,
        "driver_lat": booking.driver_lat,
        "driver_lon": booking.driver_lon,
        "pickup_name": booking.pickup_location.split("|||")[0] if booking.pickup_location else None,
        "pickup_lat": p_lat,
        "pickup_lon": p_lon,
        "dropoff_name": booking.dropoff_location.split("|||")[0] if booking.dropoff_location else None,
        "dropoff_lat": d_lat,
        "dropoff_lon": d_lon,
        "origin": booking.vehicle.origin if booking.vehicle else None,
        "destination": booking.vehicle.destination if booking.vehicle else None,
    }



@router.get("/bookings/active-enroute", response_model=list[ProviderBookingOut])
def list_active_enroute_bookings(
    user_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(ProviderBooking).filter(
        ProviderBooking.status != "cancelled",
        ProviderBooking.navigation_status.in_(["enroute", "trip_started"])
    )
    if user_id:
        query = query.filter(ProviderBooking.user_id == user_id)
    return query.all()


@router.post("/vehicles/{vehicle_id}/start-trip")
def start_vehicle_trip(vehicle_id: int, db: Session = Depends(get_db)):
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id == vehicle_id,
        ProviderBooking.status != "cancelled"
    ).all()
    for b in bookings:
        b.navigation_status = "trip_started"
        b.message_unread = True
    db.commit()
    return {"status": "success", "updated_count": len(bookings)}


@router.post("/vehicles/{vehicle_id}/location")
def update_vehicle_location(vehicle_id: int, data: LocationUpdateSchema, db: Session = Depends(get_db)):
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id == vehicle_id,
        ProviderBooking.status != "cancelled"
    ).all()
    for b in bookings:
        b.driver_lat = data.lat
        b.driver_lon = data.lon
    db.commit()
    return {"status": "success"}


# ── Traveler Provider Bookings API ──────────────────────────────────────────

@router.get("/bookings/user", response_model=list[ProviderBookingOut])
def list_user_provider_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.user_id == int(current_user["user_id"])
    ).order_by(ProviderBooking.created_at.desc()).all()
    return bookings


@router.post("/bookings/{booking_id}/cancel")
def cancel_user_provider_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(ProviderBooking).filter(
        ProviderBooking.id == booking_id,
        ProviderBooking.user_id == int(current_user["user_id"])
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")

    booking.status = "cancelled"
    
    # Release seats
    vehicle = booking.vehicle
    if vehicle:
        if vehicle.destination == "Private":
            vehicle.seats_booked = 0
        else:
            vehicle.seats_booked = max(vehicle.seats_booked - booking.num_seats, 0)

    db.commit()
    return {"status": "success", "message": "Booking cancelled"}


@router.get("/bookings/unread-check")
def check_unread_provider_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = db.query(ProviderBooking).filter(
        ProviderBooking.user_id == int(current_user["user_id"]),
        ProviderBooking.message_unread == True
    ).count()
    return {"has_unread": count > 0}


