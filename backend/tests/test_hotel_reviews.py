import pytest
from app.models.models import Hotel, HotelReview, User
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
def seed_test_hotel(db_session):
    hotel = Hotel(
        name="Taj Palace Test",
        city="Jaipur",
        address="NH-8, Jaipur",
        star_rating=4.0,
        price_per_night_inr=5000.0,
        total_rooms=10,
        rooms_booked=0,
        avg_rating=0.0,
        total_reviews=0
    )
    db_session.add(hotel)
    db_session.commit()
    db_session.refresh(hotel)
    return hotel

def test_hotel_reviews_flow(client, db_session, auth_headers, seed_test_hotel):
    hotel_id = seed_test_hotel.id
    
    # 1. Post a review
    review_data = {"rating": 5, "review_text": "Excellent stay, loved the hospitality!"}
    res = client.post(f"/api/booking/hotels/{hotel_id}/reviews", json=review_data, headers=auth_headers)
    assert res.status_code == 201
    res_data = res.json()
    assert res_data["status"] == "success"
    assert res_data["avg_rating"] == 5.0
    assert res_data["total_reviews"] == 1
    
    # 2. Post a second review
    review_data_2 = {"rating": 3, "review_text": "Average stay, could be cleaner."}
    res2 = client.post(f"/api/booking/hotels/{hotel_id}/reviews", json=review_data_2, headers=auth_headers)
    assert res2.status_code == 201
    assert res2.json()["avg_rating"] == 4.0
    assert res2.json()["total_reviews"] == 2
    
    # 3. Retrieve reviews
    res_list = client.get(f"/api/booking/hotels/{hotel_id}/reviews", headers=auth_headers)
    assert res_list.status_code == 200
    reviews = res_list.json()
    assert len(reviews) == 2
    assert reviews[0]["rating"] == 3
    assert reviews[0]["review_text"] == "Average stay, could be cleaner."
    assert reviews[0]["user_name"] == "Test User"
    assert reviews[1]["rating"] == 5
    
    # 4. Verify search results populate reviews fields
    search_data = {"city": "Jaipur", "num_rooms": 1}
    res_search = client.post("/api/booking/hotels/search", json=search_data, headers=auth_headers)
    assert res_search.status_code == 200
    search_results = res_search.json()
    # Find our test hotel
    found_hotel = next((h for h in search_results if h["id"] == hotel_id), None)
    assert found_hotel is not None
    assert found_hotel["avg_rating"] == 4.0
    assert found_hotel["total_reviews"] == 2
