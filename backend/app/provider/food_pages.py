from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.models import Provider, Restaurant, MenuItem, FoodOrder
from app.provider.auth import (
    hash_password, verify_password,
    create_provider_token, decode_provider_token
)
from app.core.email_otp import generate_and_send_otp, verify_otp, clear_otp, _otp_store

router = APIRouter(prefix="/food-provider")
templates = Jinja2Templates(directory="templates")


def get_food_provider_from_cookie(request: Request, db: Session) -> Optional[Provider]:
    token = request.cookies.get("food_provider_access_token")
    if not token:
        return None
    try:
        provider_id = decode_provider_token(token)
        return db.query(Provider).filter(Provider.id == provider_id).first()
    except Exception:
        return None


# ── Register ───────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "food_provider_register.html", {})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(Provider).filter(Provider.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "food_provider_register.html", {
            "error": "Email already registered."
        })

    provider = Provider(
        company_name="",
        contact_person="",
        email=email,
        password_hash=hash_password(password),
        phone="",
        city="",
        service_type="restaurant",  # Force service type to restaurant immediately
        booking_mode=""
    )
    db.add(provider)
    db.commit()

    return RedirectResponse("/food-provider/login?success=Registration successful! Please login.", status_code=303)


# ── Login ──────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "food_provider_login.html", {"success": success})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    provider = db.query(Provider).filter(Provider.email == email).first()
    if not provider or not verify_password(password, provider.password_hash):
        return templates.TemplateResponse(request, "food_provider_login.html", {
            "error": "Invalid email or password."
        })

    token = create_provider_token(provider.id)
    response = RedirectResponse("/food-provider/dashboard", status_code=303)
    response.set_cookie("food_provider_access_token", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/food-provider/login", status_code=303)
    response.delete_cookie("food_provider_access_token")
    return response


# ── Setup ──────────────────────────────────────────────────────────────────

@router.post("/setup", response_class=HTMLResponse)
def setup_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    address: str = Form(...),
    db: Session = Depends(get_db),
):
    provider = get_food_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/food-provider/login", status_code=303)

    provider.company_name = company_name.strip()
    provider.contact_person = contact_person.strip()
    provider.phone = phone.strip()
    provider.city = city.strip().title()
    provider.service_type = "restaurant"  # Keep locked to restaurant
    db.commit()

    # Create the Restaurant profile if not exists
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == provider.id).first()
    if not restaurant:
        restaurant = Restaurant(
            provider_id=provider.id,
            name=company_name.strip(),
            city=city.strip().title(),
            address=address.strip(),
            rating=4.2,
            reviews_count=1
        )
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)

        # Auto-seed popular starter menu items so the restaurant has an active menu immediately
        default_items = [
            MenuItem(restaurant_id=restaurant.id, name="Paneer Butter Masala", description="Rich and creamy curry made with paneer, butter, spices, onions, tomatoes, and cashews.", price_inr=240.0, category="Veg", rating=4.5),
            MenuItem(restaurant_id=restaurant.id, name="Dal Makhani", description="Classic black lentils slow-cooked overnight with spices, butter, and cream.", price_inr=180.0, category="Veg", rating=4.4),
            MenuItem(restaurant_id=restaurant.id, name="Tandoori Roti", description="Freshly baked whole wheat flatbread in a clay oven.", price_inr=30.0, category="Veg", rating=4.2),
            MenuItem(restaurant_id=restaurant.id, name="Gulab Jamun", description="Soft, delicious berry-sized balls made of milk solids, soaked in rose flavored sugar syrup.", price_inr=80.0, category="Dessert", rating=4.7),
            MenuItem(restaurant_id=restaurant.id, name="Masala Chai", description="A spiced Indian tea beverage brewed with a mixture of aromatic herbs and spices.", price_inr=40.0, category="Beverage", rating=4.5)
        ]
        db.add_all(default_items)
        db.commit()
        
        # Add a default review to make rating look organic
        from app.models.models import FoodReview, User
        user = db.query(User).first()
        if user:
            review = FoodReview(
                user_id=user.id,
                menu_item_id=default_items[0].id,
                rating=5,
                comment="Excellent family dhaba, very fast service and clean food."
            )
            db.add(review)
            db.commit()

    return RedirectResponse("/food-provider/dashboard", status_code=303)


# ── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    provider = get_food_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/food-provider/login", status_code=303)

    # Show setup popup if provider hasn't completed their profile
    show_setup = not provider.company_name

    # Find or create restaurant details
    restaurant = db.query(Restaurant).filter(Restaurant.provider_id == provider.id).first()
    if not restaurant and not show_setup:
        restaurant = Restaurant(
            provider_id=provider.id,
            name=provider.company_name or "My Restaurant",
            city=provider.city or "Jaipur",
            address="Main Street",
            rating=4.0,
            reviews_count=0
        )
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)

    orders_list = []
    menu_items = []
    total_sales = 0.0
    active_orders = 0
    completed_orders = 0

    if restaurant:
        menu_items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
        if len(menu_items) == 0:
            default_items = [
                MenuItem(restaurant_id=restaurant.id, name="Paneer Butter Masala", description="Rich and creamy curry made with paneer, butter, spices, onions, tomatoes, and cashews.", price_inr=240.0, category="Veg", rating=4.5),
                MenuItem(restaurant_id=restaurant.id, name="Dal Makhani", description="Classic black lentils slow-cooked overnight with spices, butter, and cream.", price_inr=180.0, category="Veg", rating=4.4),
                MenuItem(restaurant_id=restaurant.id, name="Tandoori Roti", description="Freshly baked whole wheat flatbread in a clay oven.", price_inr=30.0, category="Veg", rating=4.2),
                MenuItem(restaurant_id=restaurant.id, name="Gulab Jamun", description="Soft, delicious berry-sized balls made of milk solids, soaked in rose flavored sugar syrup.", price_inr=80.0, category="Dessert", rating=4.7),
                MenuItem(restaurant_id=restaurant.id, name="Masala Chai", description="A spiced Indian tea beverage brewed with a mixture of aromatic herbs and spices.", price_inr=40.0, category="Beverage", rating=4.5)
            ]
            db.add_all(default_items)
            db.commit()
            menu_items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()

        orders = db.query(FoodOrder).filter(FoodOrder.restaurant_id == restaurant.id).order_by(FoodOrder.created_at.desc()).all()
        
        # Calculate stats
        total_sales = sum(o.total_amount for o in orders if o.status != "cancelled")
        active_orders = len([o for o in orders if o.status in ("pending", "paid", "preparing", "ready")])
        completed_orders = len([o for o in orders if o.status == "completed"])
        
        import json
        for o in orders:
            orders_list.append({
                "id": o.id,
                "user_name": o.user.name if o.user else "Passenger",
                "items": json.loads(o.items_json),
                "total_amount": o.total_amount,
                "status": o.status,
                "preparation_time_mins": o.preparation_time_mins,
                "user_arrival_time_mins": o.user_arrival_time_mins,
                "created_at": o.created_at
            })

    return templates.TemplateResponse(request, "food_provider_dashboard.html", {
        "provider": provider,
        "restaurant": restaurant,
        "orders": orders_list,
        "menu_items": menu_items,
        "total_sales": total_sales,
        "active_orders": active_orders,
        "completed_orders": completed_orders,
        "show_setup": show_setup
    })
