"""
Tests for the provider AI chatbot endpoint.
"""
import pytest
from app.models.models import Provider, ProviderVehicle, ProviderBooking, User
from app.provider.auth import create_provider_token, hash_password

def test_unauthorized_chatbot_access(client):
    # Chatbot endpoint should require provider login
    response = client.post(
        "/api/provider/chat",
        json={"message": "how to add a vehicle", "history": []}
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json().get("detail", "")

def test_provider_chatbot_scope_rules(client, db_session):
    # 1. Create and authenticate provider
    provider = Provider(
        company_name="Fleet Partner Co",
        contact_person="Ramesh Kumar",
        email="partner_bot_test@roadbuddy.com",
        password_hash=hash_password("partner123"),
        phone="9876543210",
        city="Jaipur",
        service_type="cabs_buses",
        is_verified=True
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)

    token = create_provider_token(provider.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add dummy vehicle and booking to test real data retrieval
    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="suv",
        vehicle_name="Scorpio Classic",
        driver_included=True,
        origin="Jaipur",
        destination="Delhi",
        total_seats=7,
        seats_booked=2,
        fixed_fare_inr=3500.0,
        departure_time="09:00 AM",
        arrival_time="03:00 PM",
        is_active=True
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)

    user = User(
        name="John Customer",
        email="john_c@example.com",
        password_hash=hash_password("pass123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    booking = ProviderBooking(
        vehicle_id=vehicle.id,
        user_id=user.id,
        passenger_name="Rahul Sharma",
        passenger_phone="9998887776",
        passenger_email="rahul@example.com",
        travel_date="2202-08-20",
        num_seats=2,
        selected_seats="4,5",
        total_fare_inr=3000.0,
        status="confirmed"
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)

    # 2. Test valid query (Vehicle guidance - how to)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "how do I add a vehicle?", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "response" in res_data
    # Should return guidance step-by-step instructions
    assert "sidebar" in res_data["response"].lower() or "click" in res_data["response"].lower()

    # 3. Test active data query (What are my bookings - returns real info)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "what are my bookings?", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    # Should return real info directly in response
    assert "Rahul Sharma" in res_data["response"]
    assert "2202-08-20" in res_data["response"]
    assert "3000" in res_data["response"]

    # 4. Test active vehicle list query (Show my vehicles)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "show my vehicles", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "Scorpio Classic" in res_data["response"]
    assert "SUV" in res_data["response"]

    # 5. Test vehicle sub-info query (per seat fare or running times)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "what is the running time or fare of Scorpio Classic?", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "3500" in res_data["response"]
    assert "09:00 AM" in res_data["response"] or "Departs" in res_data["response"]


    # 6. Test vehicle update query (update per seat fare) - Step 1: Ask option
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "update per seat fare to 1200 of Scorpio Classic", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "manually" in res_data["response"].lower()
    assert "do it for you" in res_data["response"].lower()

    # Step 2: Choose "do it for me"
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "do it for me", "history": res_data["history"]}
    )
    assert response.status_code == 200
    res_data2 = response.json()
    assert "updated" in res_data2["response"].lower()
    assert "1200" in res_data2["response"]

    # Verify database was updated
    db_session.expire_all()
    updated_v = db_session.query(ProviderVehicle).filter(ProviderVehicle.id == vehicle.id).first()
    assert updated_v.fixed_fare_inr == 1200.0

    # 7. Test vehicle update query (update departure time) - Step 1: Ask option
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "update running time of Scorpio Classic to 11:30 AM", "history": []}
    )
    assert response.status_code == 200
    res_data3 = response.json()
    assert "manually" in res_data3["response"].lower()
    
    # Step 2: Choose "manually"
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "manually", "history": res_data3["history"]}
    )
    assert response.status_code == 200
    res_data4 = response.json()
    assert "edit button" in res_data4["response"].lower()

    # Step 3: Choose "do it for me" on timings
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "do it for me", "history": res_data3["history"]}
    )
    assert response.status_code == 200
    res_data5 = response.json()
    assert "updated" in res_data5["response"].lower()
    assert "11:30" in res_data5["response"]

    # Verify database was updated
    db_session.expire_all()
    updated_v = db_session.query(ProviderVehicle).filter(ProviderVehicle.id == vehicle.id).first()
    assert updated_v.departure_time == "11:30"


    # 8. Test strict out-of-scope query refusal

    unrelated_queries = [
        "Who is Mahatma Gandhi?",
        "write a python function to add numbers",
        "what is the weather like tomorrow?",
        "suggest a travel itinerary for Paris",
        "how to cook chocolate cake"
    ]
    for query in unrelated_queries:
        resp = client.post(
            "/api/provider/chat",
            headers=headers,
            json={"message": query, "history": []}
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "I can only answer questions related to our app."

    # 6. Test history preservation
    history_test_data = [
        {"role": "user", "content": "hello helper"},
        {"role": "assistant", "content": "Welcome! I am your RoadBuddy Partner Assistant."}
    ]
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "how do I view bookings?", "history": history_test_data}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data["history"]) == 4  # history_test_data (2) + user (1) + assistant (1)
    assert res_data["history"][-2]["content"] == "how do I view bookings?"


def test_provider_chatbot_vehicle_matching_ambiguity(client, db_session):
    # 1. Create and authenticate provider
    provider = Provider(
        company_name="Fleet Partner Co 2",
        contact_person="Ramesh Kumar",
        email="partner_bot_test_ambiguity@roadbuddy.com",
        password_hash=hash_password("partner123"),
        phone="9876543210",
        city="Jaipur",
        service_type="cabs_buses",
        is_verified=True
    )
    db_session.add(provider)
    db_session.commit()
    db_session.refresh(provider)

    token = create_provider_token(provider.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Add two vehicles with similar/overlapping names
    v1 = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="sedan",
        vehicle_name="Swift Dzire",
        driver_included=True,
        origin="Jaipur",
        destination="Delhi",
        total_seats=4,
        seats_booked=0,
        fixed_fare_inr=1500.0,
        departure_time="09:00 AM",
        arrival_time="03:00 PM",
        is_active=True
    )
    v2 = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type="sedan",
        vehicle_name="Swift VDI",
        driver_included=True,
        origin="Jaipur",
        destination="Delhi",
        total_seats=4,
        seats_booked=0,
        fixed_fare_inr=1600.0,
        departure_time="10:00 AM",
        arrival_time="04:00 PM",
        is_active=True
    )
    db_session.add(v1)
    db_session.add(v2)
    db_session.commit()

    # Test ambiguous query "update fare of Swift to 1200" (should ask to clarify or return error because of ambiguity)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "update per seat fare of Swift to 1200", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "multiple" in res_data["response"].lower() or "specify" in res_data["response"].lower()

    # Test explicit query "update per seat fare of Swift VDI to 1800" (should trigger the multi-step verification)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "update per seat fare of Swift VDI to 1800", "history": []}
    )
    assert response.status_code == 200
    res_data2 = response.json()
    assert "manually" in res_data2["response"].lower()
    
    # Confirm the update automatically
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "do it for me", "history": res_data2["history"]}
    )
    assert response.status_code == 200
    assert "updated" in response.json()["response"].lower()

    # Verify db
    db_session.expire_all()
    updated_v2 = db_session.query(ProviderVehicle).filter(ProviderVehicle.id == v2.id).first()
    assert updated_v2.fixed_fare_inr == 1800.0

