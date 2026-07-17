"""
app/routers/stations.py

REST API for fuel station availability.
Prefix: /api/stations  (registered in main.py)

Auth strategy (MVP/stub):
  - Public read endpoints: no auth required.
  - Operator write endpoints: require X-Operator-Key header matching the operator's api_key.
    # TODO (real implementation): replace stub api_key auth with a proper OAuth/JWT operator flow.
  - Crowdsource endpoint: requires existing user JWT (get_current_user).
  - Debug endpoint: gated by DEMO_MODE=true in settings; 403 in all other environments.
"""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    FuelStation,
    StationFuelType,
    AvailabilityUpdate,
    FuelStationOperator,
    ServiceRoadInfo,
    EVChargerStatus,
)
from app.services.confidence import get_best_confidence

router = APIRouter()
debug_router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class OperatorRegisterRequest(BaseModel):
    # Station fields
    station_name: str
    station_brand: Optional[str] = None
    station_latitude: float
    station_longitude: float
    station_address: Optional[str] = None
    route_tag: Optional[str] = None
    fuel_types_offered: list[str] = []  # e.g. ["petrol", "diesel", "cng"]

    # Operator / KYC fields
    operator_name: str
    phone_number: str
    license_number: Optional[str] = None
    kyc_document_reference: Optional[str] = None  # stub; no real document verification yet


class OTPVerifyRequest(BaseModel):
    otp: str  # stub — any value is accepted


class AvailabilityUpdateRequest(BaseModel):
    fuel_type: str           # petrol | diesel | cng | ev
    reported_status: str     # available | unavailable


class CrowdsourceReportRequest(BaseModel):
    fuel_type: str
    reported_status: str


class SimulateTimeRequest(BaseModel):
    station_id: int
    shift_hours: float       # shift last reported_at BACKWARD by this many hours
    fuel_type: Optional[str] = None   # if None, shifts all fuel types for the station


class EVChargerUpdateRequest(BaseModel):
    total_chargers: int
    chargers_available: int
    chargers_working: int


# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_FUEL_TYPES = {"petrol", "diesel", "cng", "ev"}
VALID_STATUSES   = {"available", "unavailable"}


def _validate_fuel_type(ft: str):
    if ft not in VALID_FUEL_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid fuel_type '{ft}'. Must be one of: {sorted(VALID_FUEL_TYPES)}"
        )


def _validate_status(s: str):
    if s not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid reported_status '{s}'. Must be one of: {sorted(VALID_STATUSES)}"
        )


def _get_operator_by_key(api_key: str, db: Session) -> FuelStationOperator:
    """Validate the X-Operator-Key header and return the matching operator."""
    # TODO (real implementation): replace this stub key check with real signed-token auth.
    if not api_key:
        raise HTTPException(status_code=401, detail="X-Operator-Key header is required.")
    op = db.query(FuelStationOperator).filter(FuelStationOperator.api_key == api_key).first()
    if not op:
        raise HTTPException(status_code=401, detail="Invalid operator key.")
    return op


def _build_station_response(station: FuelStation, db: Session) -> dict:
    """Assemble the full station detail response with live confidence scores."""
    fuel_availability = []
    for ft_row in station.fuel_types:
        # Pull only the updates for this fuel type, sorted by reported_at desc
        updates = (
            db.query(AvailabilityUpdate)
            .filter(
                AvailabilityUpdate.station_id == station.id,
                AvailabilityUpdate.fuel_type == ft_row.fuel_type,
            )
            .order_by(AvailabilityUpdate.reported_at.desc())
            .all()
        )
        confidence = get_best_confidence(updates)
        fuel_availability.append({
            "fuel_type": ft_row.fuel_type,
            "is_offered": ft_row.is_offered,
            "confidence": {
                "score": confidence["score"],
                "label": confidence["label"],
                "is_stale": confidence["is_stale"],
            },
            "last_update_source": confidence["last_update_source"],
            "last_reported_at": confidence["last_reported_at"],
            "reported_status": confidence["reported_status"],
        })

    ev_status = None
    if station.ev_charger_status:
        ev = station.ev_charger_status
        ev_status = {
            "total_chargers": ev.total_chargers,
            "chargers_available": ev.chargers_available,
            "chargers_working": ev.chargers_working,
            "last_updated_at": ev.last_updated_at.isoformat() if ev.last_updated_at else None,
        }

    service_road = None
    if station.service_road_info:
        sr = station.service_road_info
        service_road = {
            "highway_side": sr.highway_side,
            "entry_position": sr.entry_position,
            "requires_u_turn": sr.requires_u_turn,
            "entry_point_latitude": sr.entry_point_latitude,
            "entry_point_longitude": sr.entry_point_longitude,
            "notes": sr.notes,
        }

    return {
        "station": {
            "id": station.id,
            "name": station.name,
            "brand": station.brand,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "address": station.address,
            "route_tag": station.route_tag,
            "is_demo": station.is_demo,
            "created_at": station.created_at.isoformat() if station.created_at else None,
        },
        "fuel_availability": fuel_availability,
        "ev_charger_status": ev_status,
        "service_road_info": service_road,
    }


# ── Operator Registration ─────────────────────────────────────────────────────

@router.post("/operators/register", tags=["Fuel Station Availability"])
def register_operator(data: OperatorRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new fuel station and its operator.

    For the MVP/demo: verification_status is auto-set to 'demo'.
    # TODO (real implementation): send verification link / OTP after registration and
    #   run actual KYC document checks before setting status to 'verified'.
    """
    # Validate fuel types
    for ft in data.fuel_types_offered:
        _validate_fuel_type(ft)

    # Create station
    station = FuelStation(
        name=data.station_name,
        brand=data.station_brand,
        latitude=data.station_latitude,
        longitude=data.station_longitude,
        address=data.station_address,
        route_tag=data.route_tag,
        is_demo=False,   # API registrations are not demo data
    )
    db.add(station)
    db.flush()  # get station.id before committing

    # Create fuel type offerings
    for ft in data.fuel_types_offered:
        db.add(StationFuelType(station_id=station.id, fuel_type=ft, is_offered=True))

    # Generate a stub API key for operator auth
    # TODO (real implementation): send this key securely via email/SMS, not in the API response.
    stub_api_key = secrets.token_urlsafe(32)

    # Create operator record
    operator = FuelStationOperator(
        station_id=station.id,
        name=data.operator_name,
        phone_number=data.phone_number,
        license_number=data.license_number,
        kyc_document_reference=data.kyc_document_reference,  # stub field
        verification_status="demo",  # Auto-set to demo for MVP; change to "pending" in real flow
        api_key=stub_api_key,
    )
    db.add(operator)
    db.commit()
    db.refresh(station)
    db.refresh(operator)

    return {
        "message": "Operator and station registered successfully.",
        "station_id": station.id,
        "operator_id": operator.id,
        "verification_status": operator.verification_status,
        # Returning api_key in response is acceptable for demo; in production, deliver via secure channel.
        "api_key": stub_api_key,
        "note": "This is a demo registration. verification_status='demo' means no real KYC was performed.",
    }


@router.post("/operators/{operator_id}/verify-otp", tags=["Fuel Station Availability"])
def verify_operator_otp(operator_id: int, data: OTPVerifyRequest, db: Session = Depends(get_db)):
    """
    STUB endpoint — accepts any OTP value and returns success.
    # TODO (real implementation): generate a real time-limited OTP, send via SMS/email,
    #   verify it here, and only then update verification_status to 'verified'.
    """
    operator = db.query(FuelStationOperator).filter(FuelStationOperator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found.")

    # STUB: accept any OTP, no real verification
    return {
        "message": "OTP verification successful (stub — any OTP accepted in demo mode).",
        "operator_id": operator_id,
        "verification_status": operator.verification_status,
        "note": "This is a stub. Real OTP generation and verification is not yet implemented.",
    }


# ── Station Listing & Detail ──────────────────────────────────────────────────

@router.get("/", tags=["Fuel Station Availability"])
def list_stations(
    route: Optional[str] = Query(None, description="Filter by route_tag, e.g. NH48-Jaipur-Delhi"),
    fuel_type: Optional[str] = Query(None, description="Filter to stations offering this fuel type"),
    include_demo: bool = Query(True, description="Include is_demo=True stations (useful for testing)"),
    db: Session = Depends(get_db),
):
    """
    List all fuel stations, optionally filtered by route and/or fuel type.
    Returns basic info + current confidence summary per fuel type.
    """
    if fuel_type:
        _validate_fuel_type(fuel_type)

    query = db.query(FuelStation)
    if not include_demo:
        query = query.filter(FuelStation.is_demo == False)
    if route:
        query = query.filter(FuelStation.route_tag == route)
    if fuel_type:
        query = query.join(StationFuelType).filter(
            StationFuelType.fuel_type == fuel_type,
            StationFuelType.is_offered == True,
        )

    stations = query.all()

    result = []
    for s in stations:
        # Get per-fuel confidence summaries
        fuel_summaries = []
        for ft_row in s.fuel_types:
            updates = (
                db.query(AvailabilityUpdate)
                .filter(
                    AvailabilityUpdate.station_id == s.id,
                    AvailabilityUpdate.fuel_type == ft_row.fuel_type,
                )
                .order_by(AvailabilityUpdate.reported_at.desc())
                .limit(1)
                .all()
            )
            confidence = get_best_confidence(updates)
            fuel_summaries.append({
                "fuel_type": ft_row.fuel_type,
                "is_offered": ft_row.is_offered,
                "confidence_score": confidence["score"],
                "confidence_label": confidence["label"],
                "reported_status": confidence["reported_status"],
            })

        result.append({
            "id": s.id,
            "name": s.name,
            "brand": s.brand,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "route_tag": s.route_tag,
            "is_demo": s.is_demo,
            "fuel_types": fuel_summaries,
        })

    return {"stations": result, "count": len(result)}


@router.get("/{station_id}", tags=["Fuel Station Availability"])
def get_station_detail(station_id: int, db: Session = Depends(get_db)):
    """
    Full station detail: live confidence per fuel type, service road info, EV charger status.
    """
    station = db.query(FuelStation).filter(FuelStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")
    return _build_station_response(station, db)


# ── Availability Updates ──────────────────────────────────────────────────────

@router.post("/{station_id}/availability", tags=["Fuel Station Availability"])
def post_operator_availability(
    station_id: int,
    data: AvailabilityUpdateRequest,
    x_operator_key: Optional[str] = Header(None, alias="X-Operator-Key"),
    db: Session = Depends(get_db),
):
    """
    Operator posts a new availability update for their station.
    Requires X-Operator-Key header (stub auth — see _get_operator_by_key).

    Always INSERTS a new row (append-only log); never overwrites the previous record.
    """
    _validate_fuel_type(data.fuel_type)
    _validate_status(data.reported_status)

    station = db.query(FuelStation).filter(FuelStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")

    operator = _get_operator_by_key(x_operator_key, db)
    if operator.station_id != station_id:
        raise HTTPException(status_code=403, detail="Operator key does not belong to this station.")

    # APPEND — never update an existing row
    update = AvailabilityUpdate(
        station_id=station_id,
        fuel_type=data.fuel_type,
        source="operator",
        reported_status=data.reported_status,
        reported_at=datetime.now(timezone.utc),
        reported_by=operator.id,
    )
    db.add(update)
    db.commit()
    db.refresh(update)

    return {
        "message": "Availability update logged.",
        "update_id": update.id,
        "station_id": station_id,
        "fuel_type": data.fuel_type,
        "reported_status": data.reported_status,
        "reported_at": update.reported_at.isoformat(),
        "source": "operator",
        "confidence_now": 100,  # operator update resets confidence to 100%
    }


@router.post("/{station_id}/availability/crowdsource", tags=["Fuel Station Availability"])
def post_crowdsource_availability(
    station_id: int,
    data: CrowdsourceReportRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Any authenticated user can submit a crowdsourced availability report.
    Lower starting confidence (80%) and faster decay than operator updates.
    This endpoint is designed for the future driver-report feature; not used in the MVP demo
    but the schema is ready.
    """
    _validate_fuel_type(data.fuel_type)
    _validate_status(data.reported_status)

    station = db.query(FuelStation).filter(FuelStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")

    # APPEND — never update an existing row
    update = AvailabilityUpdate(
        station_id=station_id,
        fuel_type=data.fuel_type,
        source="crowdsource",
        reported_status=data.reported_status,
        reported_at=datetime.now(timezone.utc),
        reported_by=int(current_user["user_id"]),
    )
    db.add(update)
    db.commit()
    db.refresh(update)

    return {
        "message": "Crowdsourced report logged. Thank you!",
        "update_id": update.id,
        "station_id": station_id,
        "fuel_type": data.fuel_type,
        "reported_status": data.reported_status,
        "reported_at": update.reported_at.isoformat(),
        "source": "crowdsource",
        "starting_confidence": 80,
    }


# ── Service Road Info ─────────────────────────────────────────────────────────

@router.get("/{station_id}/service-road-info", tags=["Fuel Station Availability"])
def get_service_road_info(station_id: int, db: Session = Depends(get_db)):
    """Return service-road metadata for a station."""
    station = db.query(FuelStation).filter(FuelStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")
    sr = station.service_road_info
    if not sr:
        return {"station_id": station_id, "service_road_info": None}
    return {
        "station_id": station_id,
        "service_road_info": {
            "highway_side": sr.highway_side,
            "entry_position": sr.entry_position,
            "requires_u_turn": sr.requires_u_turn,
            "entry_point_latitude": sr.entry_point_latitude,
            "entry_point_longitude": sr.entry_point_longitude,
            "notes": sr.notes,
        },
    }


# ── Debug Router (DEMO_MODE only) ────────────────────────────────────────────

@debug_router.post("/debug/simulate-time", tags=["Debug (DEMO only)"])
def debug_simulate_time(data: SimulateTimeRequest, db: Session = Depends(get_db)):
    """
    ⚠️  DEBUG/DEMO ONLY ENDPOINT ⚠️
    Shifts the reported_at timestamp of the most recent availability update(s)
    backward by `shift_hours` hours, so confidence visibly drops without waiting.

    BLOCKED unless DEMO_MODE=true is set in environment.
    This endpoint must NEVER be enabled in a real production deployment.
    """
    from app.core.config import settings

    if not settings.demo_mode:
        raise HTTPException(
            status_code=403,
            detail="Debug endpoint is disabled. Set DEMO_MODE=true in environment to enable it.",
        )

    station = db.query(FuelStation).filter(FuelStation.id == data.station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")

    query = db.query(AvailabilityUpdate).filter(
        AvailabilityUpdate.station_id == data.station_id,
    )
    if data.fuel_type:
        _validate_fuel_type(data.fuel_type)
        query = query.filter(AvailabilityUpdate.fuel_type == data.fuel_type)

    # For each fuel type: find the most recent update row and shift its reported_at
    updates = query.order_by(AvailabilityUpdate.reported_at.desc()).all()

    # Group by fuel_type — only shift the latest per fuel type
    seen_fuel_types: set = set()
    shifted_count = 0
    shift_delta = timedelta(hours=data.shift_hours)

    for u in updates:
        if u.fuel_type in seen_fuel_types:
            continue
        seen_fuel_types.add(u.fuel_type)

        original_at = u.reported_at
        if original_at.tzinfo is None:
            original_at = original_at.replace(tzinfo=timezone.utc)

        u.reported_at = original_at - shift_delta
        shifted_count += 1

    db.commit()

    return {
        "message": f"Shifted reported_at backward by {data.shift_hours}h for {shifted_count} fuel type(s).",
        "station_id": data.station_id,
        "fuel_type_filter": data.fuel_type,
        "shift_hours": data.shift_hours,
        "rows_affected": shifted_count,
        "warning": "This is a destructive debug operation. Restart server or call operator update to reset.",
    }
