import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.provider.auth import get_current_provider
from app.models.models import Restaurant, MenuItem, FoodOrder, FoodReview, User, Provider

router = APIRouter()

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class FoodOrderItem(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    price: float

class OrderCreate(BaseModel):
    restaurant_id: int
    items: List[FoodOrderItem]
    total_amount: float
    payment_method: str = "prepaid"

class ArrivalUpdate(BaseModel):
    arrival_time_mins: int

class ReviewCreate(BaseModel):
    rating: int
    comment: str

class MenuItemCreate(BaseModel):
    name: str
    description: str
    price_inr: float
    category: str = "Veg"

class PrepTimeUpdate(BaseModel):
    prep_time_mins: int

class StatusUpdate(BaseModel):
    status: str


# ── Traveler Endpoints ────────────────────────────────────────────────────────

@router.get("/restaurants")
def get_restaurants(city: str, db: Session = Depends(get_db)):
    """List restaurants in a given city."""
    city_clean = city.strip()
    if not city_clean:
        return []
    # Split by comma and check first token (e.g. "Jaipur" from "Jaipur, Rajasthan, India")
    first_part = city_clean.split(",")[0].strip()
    results = db.query(Restaurant).filter(
        (Restaurant.city.ilike(f"%{first_part}%")) | 
        (Restaurant.city.ilike(f"%{city_clean}%"))
    ).all()
    if not results:
        # Fallback to checking if any restaurant city is a substring of the queried city
        all_rests = db.query(Restaurant).all()
        results = [r for r in all_rests if r.city.lower() in city_clean.lower() or city_clean.lower() in r.city.lower()]
    return results


@router.get("/restaurants/{restaurant_id}/menu")
def get_restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    """Get the menu for a restaurant including items and reviews."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
        
    items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
    results = []
    for item in items:
        # Fetch reviews for this item
        reviews = db.query(FoodReview).filter(FoodReview.menu_item_id == item.id).all()
        reviews_data = [
            {
                "id": rev.id,
                "user_name": rev.user.name if rev.user else "Anonymous",
                "rating": rev.rating,
                "comment": rev.comment,
                "created_at": str(rev.created_at)
            }
            for rev in reviews
        ]
        results.append({
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price_inr": item.price_inr,
            "category": item.category,
            "rating": item.rating,
            "reviews": reviews_data
        })
    return {
        "restaurant": {
            "id": restaurant.id,
            "name": restaurant.name,
            "city": restaurant.city,
            "address": restaurant.address,
            "rating": restaurant.rating,
            "reviews_count": restaurant.reviews_count,
            "contact_number": restaurant.contact_number
        },
        "menu_items": results
    }


@router.post("/orders", status_code=201)
def create_food_order(
    data: OrderCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Place a prepaid food order."""
    user_id = int(current_user["user_id"])
    restaurant = db.query(Restaurant).filter(Restaurant.id == data.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    items_list = [item.model_dump() for item in data.items]
    items_json = json.dumps(items_list)

    order = FoodOrder(
        user_id=user_id,
        restaurant_id=data.restaurant_id,
        items_json=items_json,
        total_amount=data.total_amount,
        status="paid",  # Prepaid is instantly marked as paid
        preparation_time_mins=20,  # Default
        user_arrival_time_mins=30,  # Default
        payment_method=data.payment_method
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders/{order_id}/arrival")
def update_arrival_time(
    order_id: int,
    data: ArrivalUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update estimated arrival offset in minutes."""
    user_id = int(current_user["user_id"])
    order = db.query(FoodOrder).filter(FoodOrder.id == order_id, FoodOrder.user_id == user_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.user_arrival_time_mins = data.arrival_time_mins
    db.commit()
    return {"success": True, "arrival_time_mins": order.user_arrival_time_mins}


@router.post("/menu-items/{item_id}/review", status_code=201)
def add_menu_item_review(
    item_id: int,
    data: ReviewCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rate and review a specific menu item."""
    user_id = int(current_user["user_id"])
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    review = FoodReview(
        user_id=user_id,
        menu_item_id=item_id,
        rating=data.rating,
        comment=data.comment
    )
    db.add(review)
    db.commit()

    # Recalculate average rating for the menu item
    all_reviews = db.query(FoodReview).filter(FoodReview.menu_item_id == item_id).all()
    avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews) if all_reviews else 4.0
    item.rating = round(avg_rating, 1)
    
    # Recalculate restaurant ratings count and average rating
    restaurant = item.restaurant
    if restaurant:
        all_menu_items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
        avg_rest_rating = sum(mi.rating for mi in all_menu_items) / len(all_menu_items) if all_menu_items else 4.0
        restaurant.rating = round(avg_rest_rating, 1)
        # Count total reviews
        total_revs = db.query(FoodReview).join(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).count()
        restaurant.reviews_count = total_revs

    db.commit()
    return {"success": True, "item_rating": item.rating}


@router.get("/my-orders")
def get_my_orders(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve current user's food orders."""
    user_id = int(current_user["user_id"])
    orders = db.query(FoodOrder).filter(FoodOrder.user_id == user_id).order_by(FoodOrder.created_at.desc()).all()
    results = []
    for order in orders:
        results.append({
            "id": order.id,
            "restaurant_name": order.restaurant.name if order.restaurant else "Restaurant",
            "restaurant_city": order.restaurant.city if order.restaurant else "Unknown",
            "items": json.loads(order.items_json),
            "total_amount": order.total_amount,
            "status": order.status,
            "preparation_time_mins": order.preparation_time_mins,
            "user_arrival_time_mins": order.user_arrival_time_mins,
            "created_at": str(order.created_at)
        })
    return results


# ── Provider Endpoints ────────────────────────────────────────────────────────

@router.get("/provider/orders")
def get_provider_orders(
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Get active/past orders for the logged-in provider's restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == current_provider.id).first()
    if not restaurant:
        # Create a default restaurant if not exists
        restaurant = Restaurant(
            provider_id=current_provider.id,
            name=current_provider.company_name or "My Restaurant",
            city=current_provider.city or "Jaipur",
            address="Main Street",
            rating=4.0,
            reviews_count=0
        )
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)

    orders = db.query(FoodOrder).filter(FoodOrder.restaurant_id == restaurant.id).order_by(FoodOrder.created_at.desc()).all()
    results = []
    for o in orders:
        user_name = o.user.name if o.user else "Passenger"
        results.append({
            "id": o.id,
            "user_name": user_name,
            "items": json.loads(o.items_json),
            "total_amount": o.total_amount,
            "status": o.status,
            "preparation_time_mins": o.preparation_time_mins,
            "user_arrival_time_mins": o.user_arrival_time_mins,
            "created_at": str(o.created_at)
        })
    return results


@router.patch("/provider/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: StatusUpdate,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Update order status."""
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == current_provider.id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant profile not found")

    order = db.query(FoodOrder).filter(FoodOrder.id == order_id, FoodOrder.restaurant_id == restaurant.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = data.status
    db.commit()
    return {"success": True, "status": order.status}


@router.patch("/provider/orders/{order_id}/prep-time")
def update_order_prep_time(
    order_id: int,
    data: PrepTimeUpdate,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Update order preparation time."""
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == current_provider.id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant profile not found")

    order = db.query(FoodOrder).filter(FoodOrder.id == order_id, FoodOrder.restaurant_id == restaurant.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.preparation_time_mins = data.prep_time_mins
    db.commit()
    return {"success": True, "preparation_time_mins": order.preparation_time_mins}


@router.post("/provider/menu", status_code=201)
def add_provider_menu_item(
    data: MenuItemCreate,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Add a new menu item to the provider's restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == current_provider.id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant profile not found")

    item = MenuItem(
        restaurant_id=restaurant.id,
        name=data.name,
        description=data.description,
        price_inr=data.price_inr,
        category=data.category,
        rating=4.0
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/provider/menu/{item_id}")
def delete_provider_menu_item(
    item_id: int,
    current_provider: Provider = Depends(get_current_provider),
    db: Session = Depends(get_db)
):
    """Delete a menu item from the provider's restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == current_provider.id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant profile not found")

    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    db.delete(item)
    db.commit()
    return {"success": True}
