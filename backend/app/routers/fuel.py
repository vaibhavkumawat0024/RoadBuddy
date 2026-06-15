from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import FuelCalcRequest, FuelCalcOut
from app.services.fuel_calculator import build_fuel_calc_response
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Vehicle

router = APIRouter()


@router.post("/calculate", response_model=FuelCalcOut)
def calculate_trip_cost(
    data: FuelCalcRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate fuel cost + NHAI toll for a route.
    Fetches real vehicle data from DB for accurate calculations.
    """
    # Fetch real vehicle from DB
    vehicle = db.query(Vehicle).filter(
        Vehicle.id == int(data.vehicle_id),
        Vehicle.user_id == int(current_user["user_id"])
    ).first()

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found. Please add a vehicle first."
        )

    vehicle_info = {
        "fuel_type":    vehicle.fuel_type,
        "mileage_kmpl": vehicle.mileage_kmpl,
        "category":     vehicle.category,
    }

    try:
        result = build_fuel_calc_response(
            origin=data.origin,
            destination=data.destination,
            vehicle=vehicle_info,
            include_return=data.include_return,
        )
        return FuelCalcOut(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fuel-prices")
def get_fuel_prices():
    """
    Get current fuel prices by type.
    In production: fetch from Indian Oil API.
    """
    return {
        "prices": {
            "petrol_per_litre_inr":  104.0,
            "diesel_per_litre_inr":   90.0,
            "cng_per_kg_inr":         85.0,
            "electric_per_kwh_inr":    8.5,
        },
        "last_updated": "2025-06-09",
        "source": "Mock data — connect Indian Oil API in production",
    }


@router.get("/toll-estimate")
def get_toll_estimate(
    origin: str,
    destination: str,
    vehicle_category: str = "car"
):
    """
    Quick toll estimate without authentication.
    Useful for the pre-login trip preview screen.
    """
    from app.services.fuel_calculator import estimate_distance, calculate_toll_cost
    distance = estimate_distance(origin, destination)
    toll = calculate_toll_cost(distance, vehicle_category)
    return {
        "origin": origin,
        "destination": destination,
        "estimated_distance_km": distance,
        "estimated_toll_inr": toll,
        "vehicle_category": vehicle_category,
    }