"""Tests for the trip completion /api/trips/{trip_id}/end endpoint."""
import pytest
from tests.conftest import create_test_user
from app.models.models import Trip, Booking, ProviderBooking, FoodOrder, Journal

def test_unauthorized_trip_end(client):
    response = client.post("/api/trips/999/end")
    assert response.status_code == 401

def test_end_trip_success(client, db_session):
    # 1. Create traveler and get auth token
    user_info = create_test_user(email="trippertest@roadbuddy.com", name="Tripper Tester")
    token = user_info["token"]
    user_id = user_info["user"].id
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add a trip record
    trip = Trip(
        user_id=user_id,
        origin="Jaipur",
        destination="Delhi",
        start_date="2026-08-20",
        budget_inr=10000.0,
        travel_mode="own_vehicle",
        status="active",
        fuel_cost_inr=1500.0,
        toll_cost_inr=400.0
    )
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)

    # 3. Add transit and hotel bookings
    booking = Booking(
        user_id=user_id,
        transport_option_id="bus_999",
        passenger_name="Tripper Tester",
        travel_date="2026-08-20",
        going_fare_inr=500.0,
        total_fare_inr=500.0,
        status="confirmed"
    )
    db_session.add(booking)

    from app.models.models import HotelBooking, Hotel
    hotel = Hotel(
        name="Test Grand Palace",
        city="Delhi",
        price_per_night_inr=4000.0,
    )
    db_session.add(hotel)
    db_session.commit()
    db_session.refresh(hotel)

    hotel_booking = HotelBooking(
        hotel_id=hotel.id,
        user_id=user_id,
        check_in_date="2026-08-20",
        check_out_date="2026-08-22",
        num_rooms=1,
        total_price_inr=8000.0,
        status="confirmed"
    )
    db_session.add(hotel_booking)
    db_session.commit()
    db_session.refresh(hotel_booking)

    # 4. Trigger the end_trip completion API
    response = client.post(f"/api/trips/{trip.id}/end", headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True

    # 5. Assert database records have correct state updates
    db_session.refresh(trip)
    assert trip.status == "completed"
    
    # Assert associated booking was transitioned to completed
    db_session.refresh(booking)
    assert booking.status == "completed"

    # Assert hotel booking was transitioned to completed
    db_session.refresh(hotel_booking)
    assert hotel_booking.status == "completed"

    # Assert journal was compiled
    journal = db_session.query(Journal).filter(Journal.trip_id == str(trip.id)).first()
    assert journal is not None
    assert journal.total_expense_inr > 0.0
