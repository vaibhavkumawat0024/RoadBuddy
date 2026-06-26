"""
Tests for the provider vehicle listing edit endpoint.
"""
import pytest
from app.models.models import Provider, ProviderVehicle
from app.provider.auth import create_provider_token, hash_password

def test_edit_vehicle_listing(client, db_session):
    # 1. Create provider
    provider = Provider(
        company_name="Jaipur Travels",
        contact_person="Ravi Verma",
        email="ravi@jaipurtravels.com",
        password_hash=hash_password("pass123"),
        phone="9876543210",
        city="Jaipur",
        service_type="cabs_buses",
        is_verified=True
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)

    # Log in by setting cookie
    token = create_provider_token(provider.id)
    client.cookies.set("provider_access_token", token)

    # 2. Create vehicle listing
    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="suv",
        vehicle_name="Innova Crysta",
        driver_included=True,
        origin="Jaipur",
        destination="Delhi",
        departure_time="08:00 AM",
        arrival_time="02:00 PM",
        total_seats=7,
        fixed_fare_inr=3000.0,
        pickup_points="Stop A;Stop B",
        dropoff_points="Stop C",
        service_dates="2026-07-01,2026-07-02",
        is_active=True
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)

    # 3. Perform edit via POST
    response = client.post(
        f"/provider/vehicles/{vehicle.id}/edit",
        data={
            "origin": "Jaipur City",
            "destination": "Delhi Airport",
            "departure_time": "09:30 AM",
            "arrival_time": "03:30 PM",
            "fixed_fare_inr": "3200",
            "pickup_points": "Stop A;Stop B;Stop D",
            "dropoff_points": "Stop C;Stop E",
            "service_dates": "2026-07-01,2026-07-02,2026-07-03"
        },
        follow_redirects=False
    )


    # Verify redirection and db updates
    assert response.status_code == 303
    assert "/provider/vehicles" in response.headers["location"]

    # Refresh DB session state
    db_session.expire_all()
    updated_vehicle = db_session.query(ProviderVehicle).filter(ProviderVehicle.id == vehicle.id).first()

    assert updated_vehicle.origin == "Jaipur City"
    assert updated_vehicle.destination == "Delhi Airport"
    assert updated_vehicle.departure_time == "09:30 AM"
    assert updated_vehicle.arrival_time == "03:30 PM"
    assert updated_vehicle.fixed_fare_inr == 3200.0
    assert updated_vehicle.pickup_points == "Stop A;Stop B;Stop D"
    assert updated_vehicle.dropoff_points == "Stop C;Stop E"
    assert updated_vehicle.service_dates == "2026-07-01,2026-07-02,2026-07-03"
