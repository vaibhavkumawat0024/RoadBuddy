from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(email="test@roadbuddy.com", password="Test123", name="Test User", home_city="Jaipur"):
    return client.post("/api/users/register", json={
        "email": email,
        "password": password,
        "name": name,
        "home_city": home_city,
    })


def login_user(email="test@roadbuddy.com", password="Test123"):
    return client.post("/api/users/login", json={
        "email": email,
        "password": password,
    })


def get_token():
    register_user()
    response = login_user()
    return response.json()["access_token"]


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_success():
    response = register_user(email="newuser@roadbuddy.com")
    assert response.status_code == 201
    assert response.json()["email"] == "newuser@roadbuddy.com"


def test_register_duplicate_email():
    register_user(email="duplicate@roadbuddy.com")
    response = register_user(email="duplicate@roadbuddy.com")
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success():
    register_user(email="logintest@roadbuddy.com")
    response = login_user(email="logintest@roadbuddy.com")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password():
    register_user(email="wrongpass@roadbuddy.com")
    response = client.post("/api/users/login", json={
        "email": "wrongpass@roadbuddy.com",
        "password": "WrongPassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user():
    response = client.post("/api/users/login", json={
        "email": "ghost@roadbuddy.com",
        "password": "Test123",
    })
    assert response.status_code == 401


# ── Profile ───────────────────────────────────────────────────────────────────

def test_get_profile():
    register_user(email="profile@roadbuddy.com")
    token = get_token()
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_get_profile_without_token():
    response = client.get("/api/users/me")
    assert response.status_code == 401 or response.status_code == 403


# ── Vehicles ──────────────────────────────────────────────────────────────────

def test_add_vehicle():
    register_user(email="vehicle@roadbuddy.com")
    response = login_user(email="vehicle@roadbuddy.com")
    token = response.json()["access_token"]

    response = client.post("/api/users/vehicles", json={
        "name": "My Car",
        "fuel_type": "petrol",
        "mileage_kmpl": 15.0,
        "category": "car",
        "tank_capacity_litres": 45.0,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["fuel_type"] == "petrol"


def test_list_vehicles():
    register_user(email="listvehicle@roadbuddy.com")
    response = login_user(email="listvehicle@roadbuddy.com")
    token = response.json()["access_token"]

    response = client.get("/api/users/vehicles", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
