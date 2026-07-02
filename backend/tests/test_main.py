def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "RoadBuddy" in response.json()["message"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chatbot_relevant_query(client):
    response = client.post("/api/trips/chat", json={"message": "Tell me about Jaipur"})
    assert response.status_code == 200
    assert "Jaipur" in response.json()["response"]


def test_chatbot_irrelevant_query(client):
    response = client.post("/api/trips/chat", json={"message": "Write a python script to sort an array"})
    assert response.status_code == 200
    assert "I am RoadBuddy AI, your road trip assistant" in response.json()["response"]


def test_chatbot_authenticated_profile(client):
    from tests.conftest import create_test_user
    res_user = create_test_user(email="chatbotuser@roadbuddy.com", name="Rahul Kumar")
    token = res_user["token"]
    
    # Query about username using auth token
    response = client.post(
        "/api/trips/chat",
        json={"message": "who am i?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    resp_text = response.json()["response"]
    assert "Rahul" in resp_text or "Rahul Kumar" in resp_text


def test_chatbot_authenticated_bookings(client):
    from tests.conftest import create_test_user, TestingSessionLocal
    from app.models.models import Hotel, HotelBooking
    
    res_user = create_test_user(email="bookinguser@roadbuddy.com", name="Amit Patel")
    token = res_user["token"]
    user_id = res_user["user"].id
    
    # Create a hotel and a booking in test DB
    db = TestingSessionLocal()
    try:
        hotel = Hotel(
            name="Taj Palace Udaipur",
            city="Udaipur",
            price_per_night_inr=5000.0,
            rooms_booked=0,
            total_rooms=10
        )
        db.add(hotel)
        db.commit()
        db.refresh(hotel)
        
        booking = HotelBooking(
            hotel_id=hotel.id,
            user_id=user_id,
            check_in_date="2026-07-01",
            check_out_date="2026-07-03",
            num_rooms=1,
            num_guests=2,
            total_price_inr=10000.0,
            status="confirmed"
        )
        db.add(booking)
        db.commit()
    finally:
        db.close()
        
    # Query about hotel booking using auth token
    response = client.post(
        "/api/trips/chat",
        json={"message": "can you show me my hotel booking details?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "Taj Palace Udaipur" in response.json()["response"]
