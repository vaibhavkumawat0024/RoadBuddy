"""Tests for the /api/community endpoints."""
from tests.conftest import create_test_user


def get_token(email="community@roadbuddy.com"):
    info = create_test_user(email=email, name="Community Tester")
    return info["token"]


def publish_a_route(client, token):
    return client.post("/api/community/routes", json={
        "trip_id": "trip_123",
        "title": "Delhi to Jaipur — Pink City Run",
        "description": "A scenic highway drive through Rajasthan.",
        "tags": ["scenic", "family-friendly"],
        "is_public": True,
    }, headers={"Authorization": f"Bearer {token}"})


def test_publish_route(client):
    token = get_token(email="publish@roadbuddy.com")
    response = publish_a_route(client, token)
    assert response.status_code == 201
    assert response.json()["title"] == "Delhi to Jaipur — Pink City Run"


def test_publish_route_without_token(client):
    response = client.post("/api/community/routes", json={
        "trip_id": "trip_123",
        "title": "Test Route",
        "description": "Test",
        "tags": [],
        "is_public": True,
    })
    assert response.status_code in (401, 403)


def test_browse_routes(client):
    response = client.get("/api/community/routes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_browse_routes_by_tag(client):
    token = get_token(email="browse@roadbuddy.com")
    publish_a_route(client, token)
    response = client.get("/api/community/routes", params={"tag": "scenic"})
    assert response.status_code == 200


def test_browse_routes_by_min_rating(client):
    response = client.get("/api/community/routes", params={"min_rating": 4.0})
    assert response.status_code == 200


def test_get_route(client):
    token = get_token(email="getroute@roadbuddy.com")
    publish_response = publish_a_route(client, token)
    route_id = publish_response.json()["id"]
    response = client.get(f"/api/community/routes/{route_id}")
    assert response.status_code == 200
    assert response.json()["id"] == route_id


def test_get_nonexistent_route(client):
    response = client.get("/api/community/routes/fake_id_999")
    assert response.status_code == 404


def test_clone_route(client):
    token = get_token(email="cloneroute@roadbuddy.com")
    publish_response = publish_a_route(client, token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/clone",
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "cloned" in response.json()["message"].lower()


def test_add_review(client):
    token = get_token(email="review@roadbuddy.com")
    publish_response = publish_a_route(client, token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/review", json={
        "route_id": route_id,
        "rating": 5,
        "review_text": "Amazing road trip!",
        "tags": ["scenic"],
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201


def test_add_invalid_rating(client):
    token = get_token(email="badrating@roadbuddy.com")
    publish_response = publish_a_route(client, token)
    route_id = publish_response.json()["id"]
    response = client.post(f"/api/community/routes/{route_id}/review", json={
        "route_id": route_id,
        "rating": 10,
        "review_text": "Too good!",
        "tags": [],
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400


def test_get_reviews(client):
    token = get_token(email="getreviews@roadbuddy.com")
    publish_response = publish_a_route(client, token)
    route_id = publish_response.json()["id"]
    response = client.get(f"/api/community/routes/{route_id}/reviews")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
