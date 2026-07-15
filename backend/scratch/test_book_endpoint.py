import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import ProviderVehicle, Provider, User
from app.provider.auth import hash_password

def run_test():
    client = TestClient(app)
    db = SessionLocal()
    try:
        # Create a test provider
        provider = db.query(Provider).filter(Provider.email == "test_book_provider@roadbuddy.com").first()
        if not provider:
            provider = Provider(
                company_name="Test Book Co",
                contact_person="John Doe",
                email="test_book_provider@roadbuddy.com",
                password_hash=hash_password("password123"),
                phone="1234567890",
                city="Delhi",
                service_type="both",
                is_verified=True
            )
            db.add(provider)
            db.commit()
            db.refresh(provider)

        # Create a test user
        user = db.query(User).filter(User.email == "test_book_passenger@roadbuddy.com").first()
        if not user:
            user = User(
                name="Test passenger",
                email="test_book_passenger@roadbuddy.com",
                password_hash=hash_password("password123")
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create a test vehicle (Dzire Private Cab)
        vehicle = ProviderVehicle(
            provider_id=provider.id,
            vehicle_type="sedan",
            vehicle_name="Dzire Book Test",
            driver_included=True,
            origin="Jaipur",
            destination="Delhi",
            total_seats=4,
            seats_booked=0,
            is_active=True,
            fixed_fare_inr=800.0
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)

        payload = {
            "vehicle_id": vehicle.id,
            "passenger_name": "kunal",
            "passenger_phone": "9999999999",
            "passenger_email": "kunal@gmail.com",
            "passenger_details": '[{"name": "kunal", "age": "99", "seat": "10"}, {"name": "vaibhav", "age": "34", "seat": "9"}]',
            "travel_date": "2026-07-08",
            "num_seats": 2,
            "pickup_location": "jaipur",
            "dropoff_location": "delhi",
            "selected_seats": "9, 10",
            "user_id": user.id,
            "total_fare_inr": 800.0
        }

        print("Sending request to /api/provider/book...")
        response = client.post("/api/provider/book", json=payload)
        print("Response status code:", response.status_code)
        print("Response JSON:", response.text)
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
