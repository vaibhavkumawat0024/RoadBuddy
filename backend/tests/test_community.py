from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(email="community@roadbuddy.com"):
    client.post("/api/users/register", json={
        "email": email,
        "password": "Test123",
        "name": "Community Tester",
        "home_city": "Mumbai",
    })
    response = client.post("/api/users/login", data={
        "username": email,
        "password": "Test123",
    })
    return response.json()["access_token"]


def publish_a_route(token):
    return client.post("/api/community/routes", json={
        "trip_id": "trip_123",
        "title": "Delhi to Jaipur — Pink City Run",
        "description": "A scenic highway drive through Rajasthan.",
        "tags": ["scenic", "family-friendly"],
        "is_public": True,
    }, headers={"Authorization": f"Bearer {token}"})


def test_publish_route():
    token = get_token(email="publish@roadbuddy.com")
    response = publish_a_route(token)
    assert response.status_code == 201
    assert response.json()["title"] == "Delhi to Jaipur — Pink City Run"


def test_publish_route_without_token():
    response = client.post("/api/community/routes", json={
        "trip_id": "trip_123",
        "title": "Test Route",
        "description": "Test",
        "tags": [],
        "is_public": True,
    })
    assert response.status_code == 401 or response.status_code == 403


def test_browse_routes():
    response = client.get("/api/community/routes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_browse_routes_by_tag():
    token = get_token(email="browse@roadbuddy.com")
    publish_a_route(token)
    response = client.get("/api/community/routes", params={"tag": "scenic"})
    assert response.status_code == 200


def test_browse_routes_by_min_rating():
    response = client.get("/api/community/routes", params={"min_rating": 4.0})
    assert response.status_code == 200


def test_get_route():
    token = get_token(email="getroute@roadbuddy.com")
    publish_response = publish_a_route(token)
    route_id = publish_response.json()["id"]
    response = client.get(f"/api/community/routes/{route_id}")
    assert response.status_code == 200
    assert response.json()["id"] == route_id


def test_get_nonexistent_route():
    response = client.get("/api/community/routes/fake_id_999")
    assert response.status_code == 404


def test_clone_route():
    token = get_token(email="cloneroute@roadbuddy.com")
    publish_response = publish_a_route(token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/clone",
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "cloned" in response.json()["message"].lower()


def test_add_review():
    token = get_token(email="review@roadbuddy.com")
    publish_response = publish_a_route(token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/review", json={
        "route_id": route_id,
        "rating": 5,
        "review_text": "Amazing road trip!",
        "tags": ["scenic"],
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201


def test_add_invalid_rating():
    token = get_token(email="badrating@roadbuddy.com")
    publish_response = publish_a_route(token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/review", json={
        "route_id": route_id,
        "rating": 10,
        "review_text": "Too good!",
        "tags": [],
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400


def test_get_reviews():
    token = get_token(email="getreviews@roadbuddy.com")
    publish_response = publish_a_route(token)
    route_id = publish_response.json()["id"]
    response = client.get(f"/api/community/routes/{route_id}/reviews")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
