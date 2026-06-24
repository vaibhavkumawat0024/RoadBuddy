"""Tests for the /api/journal endpoints."""
from tests.conftest import create_test_user


def get_token(email="journal@roadbuddy.com"):
    info = create_test_user(email=email, name="Journal Tester")
    return info["token"]


def add_entry(client, token, trip_id="trip_j_001"):
    return client.post("/api/journal/entry", json={
        "trip_id": trip_id,
        "stop_name": "Amber Fort",
        "notes": "Beautiful fort, must visit!",
        "expense_inr": 500.0,
        "lat": 26.9855,
        "lng": 75.8513,
    }, headers={"Authorization": f"Bearer {token}"})


# ── Add Entry ─────────────────────────────────────────────────────────────────

def test_add_journal_entry(client):
    token = get_token(email="addentry@roadbuddy.com")
    response = add_entry(client, token)
    assert response.status_code == 201
    assert response.json()["entry"]["stop_name"] == "Amber Fort"


def test_add_entry_without_token(client):
    response = client.post("/api/journal/entry", json={
        "trip_id": "trip_001",
        "stop_name": "Hawa Mahal",
        "notes": "Pink city!",
        "expense_inr": 200.0,
        "lat": 26.9239,
        "lng": 75.8267,
    })
    assert response.status_code in (401, 403)


# ── Get Journal ───────────────────────────────────────────────────────────────

def test_get_journal(client):
    token = get_token(email="getjournal@roadbuddy.com")
    add_entry(client, token, trip_id="trip_j_002")

    response = client.get("/api/journal/trip_j_002",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["trip_id"] == "trip_j_002"


def test_get_nonexistent_journal(client):
    token = get_token(email="nojournal@roadbuddy.com")
    response = client.get("/api/journal/fake_trip_999",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


# ── Publish Journal ───────────────────────────────────────────────────────────

def test_publish_journal(client):
    token = get_token(email="publishjournal@roadbuddy.com")
    add_entry(client, token, trip_id="trip_j_003")

    response = client.patch("/api/journal/trip_j_003/publish",
                            headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "public" in response.json()["message"].lower()


# ── Expense Summary ───────────────────────────────────────────────────────────

def test_expense_summary(client):
    token = get_token(email="summary@roadbuddy.com")
    add_entry(client, token, trip_id="trip_j_004")

    response = client.get("/api/journal/trip_j_004/summary",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "total_expense_inr" in data
    assert "num_stops" in data
    assert data["num_stops"] >= 1
