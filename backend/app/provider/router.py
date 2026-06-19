"""
Provider API Router — RoadBuddy
----------------------------------
REST endpoints for provider registration, login, and vehicle management.
Save as: app/provider/router.py
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Provider, ProviderVehicle, ProviderBooking, User
from app.provider.schemas import (
    ProviderRegister, ProviderLogin, ProviderOut,
    VehicleCreate, VehicleUpdate, VehicleOut,
    VehicleSearchRequest, VehicleSearchResult,
    ProviderBookingCreate, ProviderBookingOut,
    CabServiceResult,
)
from app.provider.auth import (
    hash_password, verify_password,
    create_provider_token, get_current_provider,
)

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


# ── Vehicle Management ────────────────────────────────────────────────────

@router.post("/vehicles", response_model=VehicleOut, status_code=201)
def add_vehicle(
    data: VehicleCreate,
    provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type=data.vehicle_type,
        vehicle_name=data.vehicle_name,
        driver_included=data.driver_included,
        origin=data.origin,
        destination=data.destination,
        departure_time=data.departure_time,
        price_per_km_inr=data.price_per_km_inr,
        fixed_fare_inr=data.fixed_fare_inr,
        total_seats=data.total_seats,
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

    if service_type == "self_drive":
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
        query = query.filter(ProviderVehicle.origin.ilike(f"%{origin}%"))
    if destination:
        # "Private" vehicles have no real destination (they're priced per-km,
        # available from a city, not tied to a fixed route) — don't exclude
        # them just because the user typed a destination for route-based search.
        query = query.filter(
            (ProviderVehicle.destination.ilike(f"%{destination}%")) |
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
        ))
    return results


@router.post("/search", response_model=list[VehicleSearchResult])
def search_vehicles(data: VehicleSearchRequest, db: Session = Depends(get_db)):
    """Search available provider vehicles for a route. Public — no auth needed."""
    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.origin.ilike(f"%{data.origin}%"),
        ProviderVehicle.destination.ilike(f"%{data.destination}%"),
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

    fare = vehicle.fixed_fare_inr if vehicle.fixed_fare_inr else (vehicle.price_per_km_inr or 0) * 100

    # NOTE: user_id hardcoded to 1 here as placeholder — wire to get_current_user in trips router
    booking = ProviderBooking(
        vehicle_id=data.vehicle_id,
        user_id=1,
        passenger_name=data.passenger_name,
        travel_date=data.travel_date,
        num_seats=data.num_seats,
        pickup_location=data.pickup_location,
        total_fare_inr=fare * data.num_seats,
    )
    vehicle.seats_booked += data.num_seats

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


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
    )
