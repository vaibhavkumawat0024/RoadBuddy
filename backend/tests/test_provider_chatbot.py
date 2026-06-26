"""
Tests for the provider AI chatbot endpoint.
"""
import pytest
from app.models.models import Provider
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

    # 2. Test valid query (Vehicle guidance)
    response = client.post(
        "/api/provider/chat",
        headers=headers,
        json={"message": "how do I add a vehicle?", "history": []}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "response" in res_data
    assert "history" in res_data
    assert "vehicle" in res_data["response"].lower() or "add" in res_data["response"].lower()

    # 3. Test strict out-of-scope query refusal
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

    # 4. Test history preservation
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
