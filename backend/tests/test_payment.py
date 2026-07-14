import pytest
import json
from tests.conftest import create_test_user
from app.models.models import Hotel, Bus, Train, Flight, ProviderVehicle, Restaurant, MenuItem
from app.models.models import HotelBooking, Booking, ProviderBooking, FoodOrder

def test_create_order_unauthorized(client):
    response = client.post("/api/payment/create-order", json={
        "amount_inr": 1500.0,
        "booking_type": "hotel",
        "details": {}
    })
    assert response.status_code == 401

def test_create_payment_order_mock(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "razorpay_key_id", "")
    monkeypatch.setattr(settings, "razorpay_key_secret", "")

    user_info = create_test_user(email="paytest@roadbuddy.com", name="Pay Tester")
    headers = {"Authorization": f"Bearer {user_info['token']}"}
    
    response = client.post("/api/payment/create-order", json={
        "amount_inr": 1500.0,
        "booking_type": "hotel",
        "details": {"hotel_id": 1}
    }, headers=headers)
    
    assert response.status_code == 200
    res_data = response.json()
    assert "order_id" in res_data
    assert res_data["amount"] == 150000
    assert res_data["mock"] is True
    assert res_data["key_id"] == "rzp_test_mockkey"


def test_verify_hotel_payment(client, db_session):
    user_info = create_test_user(email="payverify@roadbuddy.com", name="Verify Tester")
    headers = {"Authorization": f"Bearer {user_info['token']}"}
    
    # Create a hotel
    hotel = Hotel(
        name="Hotel Payment Palace",
        city="Mumbai",
        price_per_night_inr=3000.0,
        total_rooms=10,
        rooms_booked=0
    )
    db_session.add(hotel)
    db_session.commit()
    db_session.refresh(hotel)
    
    verify_payload = {
        "razorpay_order_id": "order_mock_123456",
        "razorpay_payment_id": "pay_mock_111",
        "razorpay_signature": "sig_mock",
        "booking_type": "hotel",
        "details": {
            "hotel_id": hotel.id,
            "check_in_date": "2026-09-10",
            "check_out_date": "2026-09-12",
            "num_rooms": 2,
            "num_guests": 4,
            "total_price_inr": 12000.0
        }
    }
    
    response = client.post("/api/payment/verify", json=verify_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # Assert DB has hotel booking
    booking = db_session.query(HotelBooking).filter(HotelBooking.hotel_id == hotel.id).first()
    assert booking is not None
    assert booking.status == "confirmed"
    assert booking.num_rooms == 2
    assert booking.total_price_inr == 12000.0
    
    # Assert rooms booked updated
    db_session.refresh(hotel)
    assert hotel.rooms_booked == 2

def test_verify_transit_payment(client, db_session):
    user_info = create_test_user(email="transitpay@roadbuddy.com", name="Transit Pay")
    headers = {"Authorization": f"Bearer {user_info['token']}"}
    
    bus = Bus(
        operator_name="Volvo Multi-Axle",
        bus_type="AC Sleeper",
        origin="Jaipur",
        destination="Delhi",
        departure_time="22:00",
        arrival_time="05:00",
        duration_hrs=7.0,
        fare_inr=800.0,
        total_seats=40,
        seats_booked=0
    )
    db_session.add(bus)
    db_session.commit()
    db_session.refresh(bus)
    
    verify_payload = {
        "razorpay_order_id": "order_mock_abc",
        "razorpay_payment_id": "pay_mock_def",
        "razorpay_signature": "sig_mock",
        "booking_type": "transit",
        "details": {
            "transport_option_id": f"bus_{bus.id}",
            "passenger_name": "Transit Pay",
            "travel_date": "2026-09-15",
            "going_fare_inr": 800.0,
            "total_fare_inr": 800.0,
            "selected_seats": "12",
            "travel_class": "AC Sleeper"
        }
    }
    
    response = client.post("/api/payment/verify", json=verify_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    booking = db_session.query(Booking).filter(Booking.transport_option_id == f"bus_{bus.id}").first()
    assert booking is not None
    assert booking.status == "confirmed"
    assert booking.total_fare_inr == 800.0
    
    db_session.refresh(bus)
    assert bus.seats_booked == 1

def test_verify_food_payment(client, db_session):
    user_info = create_test_user(email="foodpay@roadbuddy.com", name="Food Pay")
    headers = {"Authorization": f"Bearer {user_info['token']}"}
    
    rest = Restaurant(
        name="Hotel Highway Point",
        city="Ajmer",
        address="NH-48, Ajmer Bypass",
        rating=4.2
    )
    db_session.add(rest)
    db_session.commit()
    db_session.refresh(rest)
    
    verify_payload = {
        "razorpay_order_id": "order_mock_food",
        "razorpay_payment_id": "pay_mock_food",
        "razorpay_signature": "sig_mock",
        "booking_type": "food",
        "details": {
            "restaurant_id": rest.id,
            "items": [
                {"menu_item_id": 1, "name": "Special Paneer Thali", "quantity": 2, "price": 250.0}
            ],
            "total_price_inr": 500.0,
            "user_arrival_time_mins": 30
        }
    }
    
    response = client.post("/api/payment/verify", json=verify_payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    order = db_session.query(FoodOrder).filter(FoodOrder.restaurant_id == rest.id).first()
    assert order is not None
    assert order.status == "confirmed"
    assert order.total_amount == 500.0
    
    items = json.loads(order.items_json)
    assert len(items) == 1
    assert items[0]["menu_item_id"] == 1
