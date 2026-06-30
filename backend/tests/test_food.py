import json
import pytest
from app.models.models import Restaurant, MenuItem, FoodOrder, FoodReview, User
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


@pytest.fixture
def seed_test_restaurant(db_session):
    # Create a test restaurant
    restaurant = Restaurant(
        name="Test Highway Dhaba",
        city="Jaipur",
        address="NH-8, Mile 45, Jaipur",
        rating=4.5,
        reviews_count=1,
        latitude=26.9,
        longitude=75.8,
        contact_number="+91 9999999999"
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)

    # Create menu items
    item1 = MenuItem(
        restaurant_id=restaurant.id,
        name="Butter Paneer",
        description="Delicious creamy cheese",
        price_inr=250.0,
        category="Veg",
        rating=4.5
    )
    item2 = MenuItem(
        restaurant_id=restaurant.id,
        name="Lassi",
        description="Thick yogurt shake",
        price_inr=80.0,
        category="Beverage",
        rating=4.7
    )
    db_session.add(item1)
    db_session.add(item2)
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    return restaurant, item1, item2


def test_get_restaurants(client, seed_test_restaurant):
    response = client.get("/api/food/restaurants?city=Jaipur")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Highway Dhaba"
    assert data[0]["city"] == "Jaipur"


def test_get_restaurant_menu(client, seed_test_restaurant):
    restaurant, item1, item2 = seed_test_restaurant
    response = client.get(f"/api/food/restaurants/{restaurant.id}/menu")
    assert response.status_code == 200
    data = response.json()
    assert data["restaurant"]["name"] == "Test Highway Dhaba"
    assert len(data["menu_items"]) == 2
    assert data["menu_items"][0]["name"] == "Butter Paneer"


def test_create_food_order(client, auth_headers, seed_test_restaurant):
    restaurant, item1, item2 = seed_test_restaurant
    payload = {
        "restaurant_id": restaurant.id,
        "items": [
            {"menu_item_id": item1.id, "name": item1.name, "quantity": 2, "price": item1.price_inr},
            {"menu_item_id": item2.id, "name": item2.name, "quantity": 1, "price": item2.price_inr}
        ],
        "total_amount": 580.0,
        "payment_method": "prepaid_wallet"
    }
    response = client.post("/api/food/orders", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["restaurant_id"] == restaurant.id
    assert data["total_amount"] == 580.0
    assert data["status"] == "paid"


def test_update_arrival_time(client, auth_headers, seed_test_restaurant, db_session):
    restaurant, item1, item2 = seed_test_restaurant
    
    # Create order first
    payload = {
        "restaurant_id": restaurant.id,
        "items": [{"menu_item_id": item1.id, "name": item1.name, "quantity": 1, "price": item1.price_inr}],
        "total_amount": 250.0,
        "payment_method": "prepaid_card"
    }
    order_res = client.post("/api/food/orders", json=payload, headers=auth_headers)
    order_id = order_res.json()["id"]

    # Update arrival offset
    arrival_payload = {"arrival_time_mins": 45}
    response = client.post(f"/api/food/orders/{order_id}/arrival", json=arrival_payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["arrival_time_mins"] == 45


def test_add_menu_item_review(client, auth_headers, seed_test_restaurant):
    restaurant, item1, item2 = seed_test_restaurant
    
    review_payload = {
        "rating": 5,
        "comment": "Outstanding butter paneer! Highly recommended."
    }
    response = client.post(f"/api/food/menu-items/{item1.id}/review", json=review_payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert response.json()["item_rating"] == 5.0


def test_food_provider_registration_and_login_flow(client, db_session):
    from app.models.models import Provider

    # Test registration GET page
    response = client.get("/food-provider/register")
    assert response.status_code == 200
    assert b"Become a Restaurant Partner" in response.content

    # Test registration POST
    email = "new_rest@roadbuddy.com"
    pw = "Secret123"
    reg_response = client.post(
        "/food-provider/register",
        data={"email": email, "password": pw},
        follow_redirects=False
    )
    assert reg_response.status_code == 303
    assert "/food-provider/login" in reg_response.headers["location"]

    # Verify provider user was created in DB
    provider = db_session.query(Provider).filter(Provider.email == email).first()
    assert provider is not None
    assert provider.service_type == "restaurant"

    # Test login GET page
    login_get = client.get("/food-provider/login")
    assert login_get.status_code == 200
    assert b"Restaurant Partner Login" in login_get.content

    # Test login POST
    login_res = client.post(
        "/food-provider/login",
        data={"email": email, "password": pw},
        follow_redirects=False
    )
    assert login_res.status_code == 303
    assert "/food-provider/dashboard" in login_res.headers["location"]
    # Check that cookie was set
    assert "food_provider_access_token" in login_res.cookies
