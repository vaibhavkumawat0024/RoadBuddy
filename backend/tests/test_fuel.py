"""Tests for the /api/fuel endpoints."""
from tests.conftest import create_test_user


def get_token():
    info = create_test_user(email="fueltest@roadbuddy.com", name="Fuel Tester")
    return info["token"]


def get_vehicle_id(client, token):
    response = client.post("/api/users/vehicles", json={
        "name": "Test Car",
        "fuel_type": "petrol",
        "category": "car",
        "mileage_kmpl": 15.0,
    }, headers={"Authorization": f"Bearer {token}"})
    return response.json()["id"]

# ── Fuel Prices ───────────────────────────────────────────────────────────────

def test_get_fuel_prices(client):
    response = client.get("/api/fuel/fuel-prices")
    assert response.status_code == 200
    data = response.json()
    assert "prices" in data
    assert "petrol_per_litre_inr" in data["prices"]
    assert "diesel_per_litre_inr" in data["prices"]


# ── Toll Estimate ─────────────────────────────────────────────────────────────

def test_toll_estimate(client):
    response = client.get("/api/fuel/toll-estimate", params={
        "origin": "Delhi",
        "destination": "Jaipur",
        "vehicle_category": "car",
    })
    assert response.status_code == 200
    data = response.json()
    assert "estimated_toll_inr" in data
    assert "estimated_distance_km" in data


# ── Calculate Trip Cost ───────────────────────────────────────────────────────

def test_calculate_trip_cost(client):
    token = get_token()
    vehicle_id = get_vehicle_id(client, token)
    response = client.post("/api/fuel/calculate", json={
        "vehicle_id": vehicle_id,
        "origin": "Delhi",
        "destination": "Jaipur",
        "include_return": False,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "fuel_cost_inr" in data
    assert "toll_cost_inr" in data


def test_calculate_trip_cost_with_return(client):
    token = get_token()
    vehicle_id = get_vehicle_id(client, token)
    response = client.post("/api/fuel/calculate", json={
        "vehicle_id": vehicle_id,
        "origin": "Mumbai",
        "destination": "Pune",
        "include_return": True,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_calculate_without_token(client):
    response = client.post("/api/fuel/calculate", json={
        "vehicle_id": "v_test",
        "origin": "Delhi",
        "destination": "Agra",
        "include_return": False,
    })
    assert response.status_code in (401, 403)
