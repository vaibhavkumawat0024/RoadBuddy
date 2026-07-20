"""
app/routers/fuel_operator_pages.py

HTML page routes for the Fuel Station Operator Dashboard.
Completely separate from the Provider (cab/vehicle) dashboard.

URLs:
  GET  /fuel-operator/register   — Registration form
  POST /fuel-operator/register   — Submit registration
  GET  /fuel-operator/login      — Login form
  POST /fuel-operator/login      — Submit login
  GET  /fuel-operator/logout     — Clear cookie and redirect
  GET  /fuel-operator/dashboard  — Main operator dashboard
  POST /fuel-operator/setup      — Complete quick pump registration
  POST /fuel-operator/reverify   — Re-verify expired fuel availability timer
  POST /fuel-operator/update-availability — Update fuel availability
"""

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

from app.core.database import get_db
from app.core.config import settings
from app.models.models import (
    FuelStation,
    StationFuelType,
    AvailabilityUpdate,
    FuelStationOperator,
    ServiceRoadInfo,
)
from app.services.confidence import get_best_confidence

router = APIRouter(prefix="/fuel-operator")
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "fuel_operator_token"
TOKEN_TYPE = "fuel_operator"


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(operator_id: int) -> str:
    from datetime import timedelta
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(
        {"sub": str(operator_id), "type": TOKEN_TYPE, "exp": expire},
        settings.secret_key, algorithm="HS256"
    )


def _get_operator_from_cookie(request: Request, db: Session) -> Optional[FuelStationOperator]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != TOKEN_TYPE:
            return None
        op_id = int(payload["sub"])
        return db.query(FuelStationOperator).filter(FuelStationOperator.id == op_id).first()
    except Exception:
        return None


def _build_dashboard_data(operator: FuelStationOperator, db: Session) -> dict:
    """Assemble everything the dashboard template needs."""
    # Check if setup is needed
    if not operator.station_id or not operator.name or not operator.relationship_to_pump:
        return {
            "operator": operator,
            "station": None,
            "fuel_data": [],
            "service_road": None,
            "recent_updates": [],
            "show_setup": True,
            "expired_prompts": []
        }

    station = db.query(FuelStation).filter(FuelStation.id == operator.station_id).first()
    fuel_rows = db.query(StationFuelType).filter(StationFuelType.station_id == station.id).all()
    service_road = db.query(ServiceRoadInfo).filter(ServiceRoadInfo.station_id == station.id).first()

    fuel_data = []
    expired_prompts = []
    current_time = datetime.now(timezone.utc)

    for row in fuel_rows:
        updates = (
            db.query(AvailabilityUpdate)
            .filter(
                AvailabilityUpdate.station_id == station.id,
                AvailabilityUpdate.fuel_type == row.fuel_type,
            )
            .order_by(AvailabilityUpdate.reported_at.desc())
            .all()
        )
        conf = get_best_confidence(updates, current_time)
        fuel_data.append({
            "fuel_type": row.fuel_type,
            "is_offered": row.is_offered,
            "confidence": conf,
            "update_count": len(updates),
        })

        # Check for expired available timers to prompt re-verification
        if row.is_offered and len(updates) > 0:
            latest_update = updates[0]
            if latest_update.reported_status == "available" and latest_update.ttl_hours is not None:
                if latest_update.ttl_hours == -1.0:
                    continue  # 24/7 available never expires!

                reported_at = latest_update.reported_at
                if reported_at.tzinfo is None:
                    reported_at = reported_at.replace(tzinfo=timezone.utc)

                elapsed_seconds = (current_time - reported_at).total_seconds()
                ttl_seconds = latest_update.ttl_hours * 3600.0

                if elapsed_seconds > ttl_seconds:
                    # Timer expired, prompt operator
                    expired_prompts.append({
                        "fuel_type": row.fuel_type,
                        "ttl_hours": latest_update.ttl_hours,
                        "reported_at_str": reported_at.strftime("%I:%M %p")
                    })

    # Recent update log (last 10)
    recent_updates = (
        db.query(AvailabilityUpdate)
        .filter(AvailabilityUpdate.station_id == station.id)
        .order_by(AvailabilityUpdate.reported_at.desc())
        .limit(10)
        .all()
    )

    return {
        "operator": operator,
        "station": station,
        "fuel_data": fuel_data,
        "service_road": service_road,
        "recent_updates": recent_updates,
        "show_setup": False,
        "expired_prompts": expired_prompts
    }


# ── Register ──────────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "fuel_operator_register.html", {})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    if otp != "1234":
        return templates.TemplateResponse(request, "fuel_operator_register.html", {"error": "Invalid OTP! Use 1234."})

    # Check if email already registered
    existing = db.query(FuelStationOperator).filter(FuelStationOperator.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "fuel_operator_register.html", {"error": "This email is already registered."})

    # Create operator with email
    operator = FuelStationOperator(
        email=email,
        name="Operator (" + email.split("@")[0] + ")",
        phone_number=None,
        station_id=None,
        verification_status="demo",
        api_key=secrets.token_urlsafe(24),
        kyc_document_reference=_hash_password(password),
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)

    return RedirectResponse(
        "/fuel-operator/login?success=Registration successful! Please login with your email.",
        status_code=303
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, success: str = ""):
    return templates.TemplateResponse(request, "fuel_operator_login.html", {"success": success})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Look up operator by email
    operator = db.query(FuelStationOperator).filter(
        FuelStationOperator.email == email
    ).first()

    error = None
    if not operator:
        error = "No operator found with that email."
    elif not operator.kyc_document_reference:
        error = "This operator account has no password."
    elif not _verify_password(password, operator.kyc_document_reference):
        error = "Incorrect password."

    if error:
        return templates.TemplateResponse(request, "fuel_operator_login.html", {"error": error})

    token = _create_token(operator.id)
    response = RedirectResponse("/fuel-operator/dashboard", status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/fuel-operator/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# ── Quick Setup ───────────────────────────────────────────────────────────────

@router.post("/setup", response_class=HTMLResponse)
def setup_submit(
    request: Request,
    operator_name: str = Form(...),
    relationship_to_pump: str = Form(...),
    gov_id: Optional[str] = Form(None),
    personal_phone: Optional[str] = Form(None),
    fuel_types: list[str] = Form(default=[]),
    dealership_name: str = Form(...),
    dealership_agreement_number: Optional[str] = Form(None),
    gstin: Optional[str] = Form(None),
    station_name: str = Form(...),
    station_address: str = Form(""),
    route_tag: str = Form(""),
    station_latitude: float = Form(...),
    station_longitude: float = Form(...),
    location_verified: bool = Form(False),
    existing_station_id: Optional[int] = Form(None),
    highway_side: str = Form("left"),
    entry_position: str = Form("before_pump"),
    requires_u_turn: bool = Form(False),
    entry_point_latitude: Optional[float] = Form(None),
    entry_point_longitude: Optional[float] = Form(None),
    service_road_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    operator = _get_operator_from_cookie(request, db)
    if not operator:
        return RedirectResponse("/fuel-operator/login", status_code=303)

    # 1. Load or Create Station
    if existing_station_id:
        station = db.query(FuelStation).filter(FuelStation.id == existing_station_id).first()
        if station:
            # Update fields on the existing station
            station.name = station_name
            station.brand = dealership_name
            station.latitude = station_latitude
            station.longitude = station_longitude
            station.address = station_address or None
            station.route_tag = route_tag or None
            station.gstin = gstin or None
            station.location_verified = location_verified
        else:
            existing_station_id = None

    if not existing_station_id:
        station = FuelStation(
            name=station_name,
            brand=dealership_name,
            latitude=station_latitude,
            longitude=station_longitude,
            address=station_address or None,
            route_tag=route_tag or None,
            gstin=gstin or None,
            location_verified=location_verified,
            is_demo=False,
        )
        db.add(station)
        db.flush()

    # 2. Add selected fuel types as offered
    # Clear old ones if it's an existing station
    if existing_station_id:
        db.query(StationFuelType).filter(StationFuelType.station_id == station.id).delete()

    valid_types = {"petrol", "diesel", "cng", "ev"}
    for ft in fuel_types:
        if ft in valid_types:
            db.add(StationFuelType(station_id=station.id, fuel_type=ft, is_offered=True))

    # 3. Create or Update Service Road Info
    sr = None
    if existing_station_id:
        sr = db.query(ServiceRoadInfo).filter(ServiceRoadInfo.station_id == station.id).first()

    if sr:
        sr.highway_side = highway_side
        sr.entry_position = entry_position
        sr.requires_u_turn = requires_u_turn
        sr.entry_point_latitude = entry_point_latitude
        sr.entry_point_longitude = entry_point_longitude
        sr.notes = service_road_notes or None
    else:
        sr = ServiceRoadInfo(
            station_id=station.id,
            highway_side=highway_side,
            entry_position=entry_position,
            requires_u_turn=requires_u_turn,
            entry_point_latitude=entry_point_latitude,
            entry_point_longitude=entry_point_longitude,
            notes=service_road_notes or None,
        )
        db.add(sr)

    # 4. Update Operator details and link station
    operator.station_id = station.id
    operator.name = operator_name
    operator.phone_number = personal_phone or ""
    operator.relationship_to_pump = relationship_to_pump
    operator.gov_id = gov_id or None
    operator.dealership_agreement_number = dealership_agreement_number or None
    operator.license_number = dealership_agreement_number or None # Sync for backward compatibility
    
    db.commit()

    return RedirectResponse("/fuel-operator/dashboard?setup_completed=1", status_code=303)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    operator = _get_operator_from_cookie(request, db)
    if not operator:
        return RedirectResponse("/fuel-operator/login", status_code=303)

    data = _build_dashboard_data(operator, db)
    
    # Query all stations (or filter out stations that already have an operator linked)
    # to list as potential link targets for quick setup.
    existing_stations = db.query(FuelStation).all()
    data["existing_stations"] = existing_stations
    
    data["MAPBOX_ACCESS_TOKEN"] = settings.mapbox_access_token
    return templates.TemplateResponse(request, "fuel_operator_dashboard.html", data)


@router.post("/update-availability", response_class=HTMLResponse)
def update_availability(
    request: Request,
    fuel_type: str = Form(...),
    reported_status: str = Form(...),
    ttl_hours: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    operator = _get_operator_from_cookie(request, db)
    if not operator:
        return RedirectResponse("/fuel-operator/login", status_code=303)

    valid_types   = {"petrol", "diesel", "cng", "ev"}
    valid_statuses = {"available", "unavailable"}
    if fuel_type not in valid_types or reported_status not in valid_statuses:
        data = _build_dashboard_data(operator, db)
        data["error"] = "Invalid fuel type or status."
        return templates.TemplateResponse(request, "fuel_operator_dashboard.html", data)

    final_ttl = None
    if reported_status == "available":
        final_ttl = ttl_hours if ttl_hours is not None else 1.0

    # APPEND-ONLY — always insert a new row
    db.add(AvailabilityUpdate(
        station_id=operator.station_id,
        fuel_type=fuel_type,
        source="operator",
        reported_status=reported_status,
        reported_at=datetime.now(timezone.utc),
        reported_by=operator.id,
        ttl_hours=final_ttl,
    ))
    db.commit()

    return RedirectResponse("/fuel-operator/dashboard?updated=1", status_code=303)


@router.post("/reverify", response_class=HTMLResponse)
def reverify_availability(
    request: Request,
    fuel_type: str = Form(...),
    still_available: str = Form(...),  # yes | no
    new_ttl_hours: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    operator = _get_operator_from_cookie(request, db)
    if not operator:
        return RedirectResponse("/fuel-operator/login", status_code=303)

    if still_available == "no":
        db.add(AvailabilityUpdate(
            station_id=operator.station_id,
            fuel_type=fuel_type,
            source="operator",
            reported_status="unavailable",
            reported_at=datetime.now(timezone.utc),
            reported_by=operator.id,
            ttl_hours=None,
        ))
    else:
        final_ttl = new_ttl_hours if new_ttl_hours is not None else 1.0
        db.add(AvailabilityUpdate(
            station_id=operator.station_id,
            fuel_type=fuel_type,
            source="operator",
            reported_status="available",
            reported_at=datetime.now(timezone.utc),
            reported_by=operator.id,
            ttl_hours=final_ttl,
        ))
    db.commit()

    return RedirectResponse("/fuel-operator/dashboard?updated=1", status_code=303)
