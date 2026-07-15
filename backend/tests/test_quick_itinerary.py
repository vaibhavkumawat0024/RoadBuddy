import pytest
from app.models.models import User
from app.core.auth import create_access_token
from app.provider.auth import hash_password

@pytest.fixture
def auth_headers(db_session):
    # Ensure there is a user
    user = db_session.query(User).filter(User.email == "tester@roadbuddy.com").first()
    if not user:
        user = User(
            name="Test User",
            email="tester@roadbuddy.com",
            password_hash=hash_password("password")
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}

def test_quick_itinerary_flow(client, auth_headers):
    # 1. Valid request
    payload = {"destination": "Manali", "days": 3}
    res = client.post("/api/trips/quick-itinerary", json=payload, headers=auth_headers)
    assert res.status_code == 200
    res_data = res.json()
    assert "destination" in res_data
    assert res_data["destination"] == "Manali"
    assert res_data["days_count"] == 3
    assert len(res_data["itinerary"]) == 3

    # 2. Invalid destination (empty)
    payload_invalid_dest = {"destination": "", "days": 3}
    res_err = client.post("/api/trips/quick-itinerary", json=payload_invalid_dest, headers=auth_headers)
    assert res_err.status_code == 400

    # 3. Invalid days (boundary validation)
    payload_invalid_days = {"destination": "Goa", "days": 20}
    res_err_days = client.post("/api/trips/quick-itinerary", json=payload_invalid_days, headers=auth_headers)
    assert res_err_days.status_code == 400
