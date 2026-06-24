"""Tests for the /api/provider/vehicles/<id>/booking-details endpoint."""
import pytest
from app.models.models import Provider, ProviderVehicle, ProviderBooking, User
from app.provider.auth import create_provider_token, hash_password


def test_booking_details_endpoint(client, db_session):
    # 1. Create a test provider
    provider = Provider(
        company_name="Test Transport Co",
        contact_person="John Doe",
        email="provider_test_details@roadbuddy.com",
        password_hash=hash_password("password123"),
        phone="1234567890",
        city="Delhi",
        service_type="both",
        is_verified=True
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)

    # 2. Create another provider (for unauthorized access test)
    other_provider = Provider(
        company_name="Other Transport",
        email="other_provider_details@roadbuddy.com",
        password_hash=hash_password("password123")
    )
    db_session.add(other_provider)
    db_session.commit()
    db_session.refresh(other_provider)

    # 3. Create a test user
    user = User(
        name="Test Passenger",
        email="passenger_test_details@roadbuddy.com",
        password_hash=hash_password("password123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 4. Create a public vehicle (Bus)
    public_vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="luxury_bus",
        vehicle_name="Test Volvo Bus",
        driver_included=True,
        origin="Delhi",
        destination="Jaipur",
        departure_time="08:00 AM",
        total_seats=40,
        seats_booked=3,
        is_active=True
    )
    db_session.add(public_vehicle)

    # 5. Create a private vehicle (Cab)
    private_vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="sedan",
        vehicle_name="Test Dzire Private",
        driver_included=True,
        origin="Delhi",
        destination="Private",
        total_seats=4,
        seats_booked=4,
        is_active=True
    )
    db_session.add(private_vehicle)
    db_session.commit()
    db_session.refresh(public_vehicle)
    db_session.refresh(private_vehicle)

    # 6. Create bookings for the public vehicle
    booking_public = ProviderBooking(
        vehicle_id=public_vehicle.id,
        user_id=user.id,
        passenger_name="Alice Smith",
        passenger_phone="9999999999",
        passenger_email="alice@example.com",
        passenger_details='[{"seat": "12", "name": "Alice Smith", "age": 25}, {"seat": "13", "name": "Charlie Doe", "age": 22}]',
        travel_date="2026-07-10",
        num_seats=2,
        selected_seats="12, 13",
        total_fare_inr=1500.0,
        status="confirmed"
    )
    db_session.add(booking_public)

    # 7. Create bookings for the private vehicle
    booking_private = ProviderBooking(
        vehicle_id=private_vehicle.id,
        user_id=user.id,
        passenger_name="Bob Brown",
        passenger_phone="8888888888",
        passenger_email="bob@example.com",
        travel_date="2026-07-11",
        num_seats=1,
        pickup_location="Delhi Airport|||28.5562,77.1000",
        dropoff_location="Jaipur Hotel|||26.9124,75.7873",
        total_fare_inr=4000.0,
        status="confirmed"
    )
    db_session.add(booking_private)
    db_session.commit()

    # Generate token
    token = create_provider_token(provider.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Generate token for other provider
    other_token = create_provider_token(other_provider.id)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Test case A: Unauthenticated request
    res = client.get(f"/api/provider/vehicles/{public_vehicle.id}/booking-details")
    assert res.status_code == 401

    # Test case B: Unauthorized access (accessing another provider's vehicle)
    res = client.get(f"/api/provider/vehicles/{public_vehicle.id}/booking-details", headers=other_headers)
    assert res.status_code == 404

    # Test case C: Successful retrieval of public vehicle details
    res = client.get(f"/api/provider/vehicles/{public_vehicle.id}/booking-details", headers=headers)
    assert res.status_code == 200
    details = res.json()
    assert details["id"] == public_vehicle.id
    assert details["vehicle_name"] == "Test Volvo Bus"
    assert details["is_public"] is True
    assert "12" in details["booked_seats"]
    assert "13" in details["booked_seats"]
    
    # We split passengers by seat occupant details in the details modal endpoint
    assert len(details["passengers"]) == 2
    assert details["passengers"][0]["name"] == "Alice Smith"
    assert details["passengers"][0]["age"] == 25
    assert details["passengers"][0]["seats"] == ["12"]
    
    assert details["passengers"][1]["name"] == "Charlie Doe"
    assert details["passengers"][1]["age"] == 22
    assert details["passengers"][1]["seats"] == ["13"]

    # Test database model properties
    assert booking_public.passenger_details_parsed == [
        {"seat": "12", "name": "Alice Smith", "age": 25},
        {"seat": "13", "name": "Charlie Doe", "age": 22}
    ]

    # Test case D: Successful retrieval of private vehicle details
    res = client.get(f"/api/provider/vehicles/{private_vehicle.id}/booking-details", headers=headers)
    assert res.status_code == 200
    details = res.json()
    assert details["id"] == private_vehicle.id
    assert details["vehicle_name"] == "Test Dzire Private"
    assert details["is_public"] is False
    assert len(details["passengers"]) == 1
    assert details["passengers"][0]["name"] == "Bob Brown"
    assert details["passengers"][0]["destination"] == "Jaipur Hotel"
