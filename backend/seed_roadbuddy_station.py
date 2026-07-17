"""
seed_roadbuddy_station.py

Seeds the single "RoadBuddy Fuel Station" on the Jaipur-Delhi route
(coordinates directly on the highway path between Dausa and Alwar: 27.25, 76.70).
is_demo = True.

Usage:
    python seed_roadbuddy_station.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.models.models import (
    FuelStation, StationFuelType, AvailabilityUpdate,
    FuelStationOperator, ServiceRoadInfo,
)

STATION = {
    "name":      "RoadBuddy Fuel Station",
    "brand":     "RoadBuddy",
    "latitude":  27.270711,     # Snapped directly on the route line near Nangal Sohan
    "longitude": 76.770233,
    "address":   "NH48, Alwar-Jaipur Highway, Rajasthan - DEMO STATION",
    "route_tag": "NH48-Jaipur-Delhi",
    "is_demo":   True,
}

OPERATOR = {
    "name":                   "RoadBuddy Operator",
    "phone_number":           "9800000001",
    "license_number":         "TEST-LIC-RB-001",
    "kyc_document_reference": None,
    "verification_status":    "demo",
    "api_key":                "demo-api-key-roadbuddy-2026",
}

AVAILABILITY = [
    {"fuel_type": "petrol", "reported_status": "available"},
    {"fuel_type": "diesel", "reported_status": "available"},
    {"fuel_type": "cng",    "reported_status": "unavailable"},
]

SERVICE_ROAD = {
    "highway_side":          "left",
    "entry_position":        "before_pump",
    "requires_u_turn":       False,
    "entry_point_latitude":  27.248,
    "entry_point_longitude": 76.698,
    "notes": "Look for the RoadBuddy green board. DEMO STATION.",
}


def seed():
    db = SessionLocal()
    try:
        # Avoid duplicates
        existing = db.query(FuelStation).filter(
            FuelStation.name == STATION["name"],
            FuelStation.is_demo == True,
        ).first()
        if existing:
            print(f"Alwar demo station already exists (id={existing.id}). Skipping.")
            return

        print("Seeding RoadBuddy Fuel Station...")

        station = FuelStation(**STATION)
        db.add(station)
        db.flush()
        print(f"   Station created (id={station.id}): {station.name}")

        for item in AVAILABILITY:
            db.add(StationFuelType(station_id=station.id, fuel_type=item["fuel_type"], is_offered=True))
        print(f"   Fuel types: petrol, diesel, cng")

        operator = FuelStationOperator(station_id=station.id, **OPERATOR)
        db.add(operator)
        db.flush()
        print(f"   Operator created (id={operator.id}): {operator.name}")

        now = datetime.now(timezone.utc)
        for item in AVAILABILITY:
            db.add(AvailabilityUpdate(
                station_id=station.id,
                fuel_type=item["fuel_type"],
                source="operator",
                reported_status=item["reported_status"],
                reported_at=now,
                reported_by=operator.id,
            ))
        print(f"   Initial availability logged (confidence=100%)")

        sr = ServiceRoadInfo(station_id=station.id, **SERVICE_ROAD)
        db.add(sr)
        print(f"   Service road info added")

        db.commit()

        print()
        print("=" * 60)
        print(f"Demo station ready!")
        print(f"   Station ID   : {station.id}")
        print(f"   Operator ID  : {operator.id}")
        print(f"   API key      : {operator.api_key}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
