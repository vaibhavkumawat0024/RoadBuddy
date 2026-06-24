"""Tests for the /api/users endpoints."""
from tests.conftest import create_test_user


# ── Register (OTP flow — only sends OTP, does NOT create user) ───────────────

def test_register_returns_otp_sent(client):
    response = client.post("/api/users/register", json={
        "email": "newuser@roadbuddy.com",
        "password": "Test123",
        "name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "OTP sent"
    assert data["email"] == "newuser@roadbuddy.com"


def test_register_duplicate_email(client):
    """If the email already exists in DB, register should return 400."""
    create_test_user(email="duplicate@roadbuddy.com")
    response = client.post("/api/users/register", json={
        "email": "duplicate@roadbuddy.com",
        "password": "Test123",
        "name": "Dup User",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    create_test_user(email="logintest@roadbuddy.com", password="Test123")
    response = client.post("/api/users/login", data={
        "username": "logintest@roadbuddy.com",
        "password": "Test123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    create_test_user(email="wrongpass@roadbuddy.com", password="CorrectPass")
    response = client.post("/api/users/login", data={
        "username": "wrongpass@roadbuddy.com",
        "password": "WrongPassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post("/api/users/login", data={
        "username": "ghost@roadbuddy.com",
        "password": "Test123",
    })
    assert response.status_code == 401


# ── Profile ───────────────────────────────────────────────────────────────────

def test_get_profile(client):
    info = create_test_user(email="profile@roadbuddy.com")
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {info['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "profile@roadbuddy.com"


def test_get_profile_without_token(client):
    response = client.get("/api/users/me")
    assert response.status_code in (401, 403)


# ── Vehicles ──────────────────────────────────────────────────────────────────

def test_add_vehicle(client):
    info = create_test_user(email="vehicle@roadbuddy.com")
    response = client.post("/api/users/vehicles", json={
        "name": "My Car",
        "fuel_type": "petrol",
        "mileage_kmpl": 15.0,
        "category": "car",
        "tank_capacity_litres": 45.0,
    }, headers={"Authorization": f"Bearer {info['token']}"})
    assert response.status_code == 201
    assert response.json()["fuel_type"] == "petrol"


def test_list_vehicles(client):
    info = create_test_user(email="listvehicle@roadbuddy.com")
    response = client.get(
        "/api/users/vehicles",
        headers={"Authorization": f"Bearer {info['token']}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)