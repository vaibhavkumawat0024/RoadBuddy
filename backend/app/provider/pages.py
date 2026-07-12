"""
Provider Page Routes — RoadBuddy
-----------------------------------
HTML page routes for the provider web interface.
Save as: app/provider/pages.py

Add to main.py:
    from app.provider.pages import router as provider_pages_router
    app.include_router(provider_pages_router)
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.models import Provider, ProviderVehicle, ProviderBooking, ProviderVehicleAsset
from app.provider.auth import (
    hash_password, verify_password,
    create_provider_token, get_provider_from_cookie,
)
from app.provider.router import _auto_cleanup_expired_routes
from app.core.email_otp import generate_and_send_otp, verify_otp, clear_otp, _otp_store

router = APIRouter(prefix="/provider")
templates = Jinja2Templates(directory="templates")


def check_provider_unread_bookings(provider, db: Session) -> bool:
    if not provider:
        return False
    vehicles = db.query(ProviderVehicle).filter(ProviderVehicle.provider_id == provider.id).all()
    vehicle_ids = [v.id for v in vehicles]
    if not vehicle_ids:
        return False
    return db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id.in_(vehicle_ids),
        ProviderBooking.provider_unread == True
    ).count() > 0


# ── Register ───────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "provider_register.html", {})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(Provider).filter(Provider.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "provider_register.html", {
            "error": "Email already registered."
        })

    provider = Provider(
        company_name="",
        contact_person="",
        email=email,
        password_hash=hash_password(password),
        phone="",
        city="",
        service_type="",
    )
    db.add(provider)
    db.commit()

    return RedirectResponse("/provider/login?success=Registration successful! Please login.", status_code=303)


# ── Login ──────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "provider_login.html", {"success": success})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    provider = db.query(Provider).filter(Provider.email == email).first()
    if not provider or not verify_password(password, provider.password_hash):
        return templates.TemplateResponse(request, "provider_login.html", {
            "error": "Invalid email or password."
        })

    token = create_provider_token(provider.id)
    response = RedirectResponse("/provider/dashboard", status_code=303)
    response.set_cookie("provider_access_token", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/provider/login", status_code=303)
    response.delete_cookie("provider_access_token")
    return response


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "provider_forgot_password.html", {})


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(Provider.email == email).first()
    if not provider:
        return templates.TemplateResponse(request, "provider_forgot_password.html", {
            "error": "No partner account registered with this email address."
        })
    try:
        generate_and_send_otp(email, provider.company_name or provider.email)
    except ValueError as e:
        return templates.TemplateResponse(request, "provider_forgot_password.html", {
            "error": str(e)
        })
    return templates.TemplateResponse(request, "provider_forgot_password_reset.html", {
        "email": email
    })


@router.post("/forgot-password/reset", response_class=HTMLResponse)
def forgot_password_reset_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(Provider.email == email).first()
    if not provider:
        return templates.TemplateResponse(request, "provider_forgot_password.html", {
            "error": "No partner account registered with this email address."
        })

    if not verify_otp(email, otp):
        return templates.TemplateResponse(request, "provider_forgot_password_reset.html", {
            "email": email,
            "error": "Invalid or expired OTP code. Please try again."
        })

    if len(new_password) < 8:
        return templates.TemplateResponse(request, "provider_forgot_password_reset.html", {
            "email": email,
            "error": "New password must be at least 8 characters long."
        })

    provider.password_hash = hash_password(new_password)
    db.commit()
    clear_otp(email)

    return RedirectResponse("/provider/login?success=Password reset successfully! Please login with your new password.", status_code=303)


@router.post("/register/send-otp")
def provider_send_otp(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters long."}
    existing = db.query(Provider).filter(Provider.email == email).first()
    if existing:
        return {"success": False, "error": "Email already registered."}
    try:
        generate_and_send_otp(email, "Partner")
    except ValueError as e:
        return {"success": False, "error": str(e)}
    _otp_store[email]["password"] = hash_password(password)
    return {"success": True}


@router.post("/register/verify-otp")
def provider_verify_otp(
    email: str = Form(...),
    otp: str = Form(...),
):
    if not verify_otp(email, otp):
        return {"success": False, "error": "Invalid or expired OTP."}
    return {"success": True}


# ── Quick Setup (first-time profile completion) ───────────────────────────

@router.post("/setup", response_class=HTMLResponse)
def setup_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    alternate_email: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    service_type: str = Form(...),
    booking_mode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    provider.company_name = company_name
    provider.contact_person = contact_person
    provider.phone = phone
    provider.alternate_email = alternate_email
    provider.city = city or ""
    provider.service_type = service_type
    provider.booking_mode = booking_mode
    db.commit()

    return RedirectResponse("/provider/dashboard", status_code=303)


# ── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    # Show setup popup if provider hasn't completed their profile
    show_setup = not provider.company_name

    if provider.service_type == "restaurant":
        from app.models.models import Restaurant, MenuItem, FoodOrder
        # Find or create restaurant
        restaurant = db.query(Restaurant).filter(Restaurant.provider_id == provider.id).first()
        if not restaurant:
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
            
        orders = db.query(FoodOrder).filter(FoodOrder.restaurant_id == restaurant.id).order_by(FoodOrder.created_at.desc()).all()
        menu_items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant.id).all()
        
        # Calculate stats
        total_sales = sum(o.total_amount for o in orders if o.status != "cancelled")
        active_orders = len([o for o in orders if o.status in ("pending", "paid", "preparing", "ready")])
        completed_orders = len([o for o in orders if o.status == "completed"])
        
        import json
        parsed_orders = []
        for o in orders:
            parsed_orders.append({
                "id": o.id,
                "user_name": o.user.name if o.user else "Passenger",
                "items": json.loads(o.items_json),
                "total_amount": o.total_amount,
                "status": o.status,
                "preparation_time_mins": o.preparation_time_mins,
                "user_arrival_time_mins": o.user_arrival_time_mins,
                "created_at": o.created_at
            })
            
        return templates.TemplateResponse(request, "provider_restaurant_dashboard.html", {
            "provider": provider,
            "restaurant": restaurant,
            "orders": parsed_orders,
            "menu_items": menu_items,
            "total_sales": total_sales,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "show_setup": show_setup
        })

    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()

    vehicle_ids = [v.id for v in vehicles]
    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id.in_(vehicle_ids)
    ).all() if vehicle_ids else []

    total_revenue = sum(b.total_fare_inr for b in bookings)
    total_seats_booked = sum(b.num_seats for b in bookings)

    return templates.TemplateResponse(request, "provider_dashboard.html", {
        "provider": provider,
        "vehicles": vehicles,
        "vehicle_count": len(vehicles),
        "total_bookings": len(bookings),
        "total_seats_booked": total_seats_booked,
        "total_revenue": total_revenue,
        "show_setup": show_setup,
        "has_unread_bookings": check_provider_unread_bookings(provider, db),
    })


# ── Vehicles ───────────────────────────────────────────────────────────────

@router.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    _auto_cleanup_expired_routes(db)
    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()

    # Query vehicle assets too
    vehicle_assets = db.query(ProviderVehicleAsset).filter(
        ProviderVehicleAsset.provider_id == provider.id
    ).all()

    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "provider_vehicles.html", {
        "provider": provider,
        "vehicles": vehicles,
        "vehicle_assets": vehicle_assets,
        "success": success,
        "has_unread_bookings": check_provider_unread_bookings(provider, db),
    })


@router.post("/vehicle-assets", response_class=HTMLResponse)
def add_vehicle_asset_submit(
    request: Request,
    vehicle_type: str = Form(...),
    vehicle_name: str = Form(...),
    total_seats: int = Form(...),
    driver_included: str = Form("true"),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    asset = ProviderVehicleAsset(
        provider_id=provider.id,
        vehicle_type=vehicle_type,
        vehicle_name=vehicle_name,
        driver_included=(driver_included == "true"),
        total_seats=total_seats,
    )
    db.add(asset)
    db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle added to fleet successfully!", status_code=303)


@router.post("/vehicle-assets/{asset_id}/delete")
def delete_vehicle_asset_submit(
    asset_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    asset = db.query(ProviderVehicleAsset).filter(
        ProviderVehicleAsset.id == asset_id,
        ProviderVehicleAsset.provider_id == provider.id,
    ).first()
    if asset:
        # Nullify reference on any active listings/vehicles
        db.query(ProviderVehicle).filter(
            ProviderVehicle.vehicle_asset_id == asset_id
        ).update({ProviderVehicle.vehicle_asset_id: None})
        db.delete(asset)
        db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle deleted from fleet.", status_code=303)


@router.post("/vehicles", response_class=HTMLResponse)
def add_vehicle_submit(
    request: Request,
    vehicle_type: Optional[str] = Form(None),
    vehicle_name: Optional[str] = Form(None),
    origin: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    departure_time: Optional[str] = Form(None),
    arrival_time: Optional[str] = Form(None),
    total_seats: Optional[int] = Form(None),
    fixed_fare_inr: Optional[float] = Form(None),
    price_per_km_inr: Optional[float] = Form(None),
    driver_included: str = Form("true"),
    pickup_points: Optional[str] = Form(None),
    dropoff_points: Optional[str] = Form(None),
    service_dates: Optional[str] = Form(None),
    vehicle_asset_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    v_type = vehicle_type
    v_name = vehicle_name
    v_driver = (driver_included == "true")
    v_seats = total_seats

    if vehicle_asset_id:
        asset = db.query(ProviderVehicleAsset).filter(
            ProviderVehicleAsset.id == vehicle_asset_id,
            ProviderVehicleAsset.provider_id == provider.id
        ).first()
        if asset:
            v_type = asset.vehicle_type
            v_name = asset.vehicle_name
            v_driver = asset.driver_included
            v_seats = asset.total_seats

    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_asset_id=vehicle_asset_id,
        vehicle_type=v_type or "sedan",
        vehicle_name=v_name or "Vehicle",
        driver_included=v_driver,
        origin=origin or "Unknown",
        destination=destination or "Private",
        departure_time=departure_time,
        arrival_time=arrival_time,
        fixed_fare_inr=fixed_fare_inr,
        price_per_km_inr=price_per_km_inr,
        total_seats=v_seats or 4,
        pickup_points=pickup_points,
        dropoff_points=dropoff_points,
        service_dates=service_dates,
    )
    db.add(vehicle)
    db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle listing added successfully!", status_code=303)


@router.post("/vehicles/{vehicle_id}/delete")
def delete_vehicle(vehicle_id: int, request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    vehicle = db.query(ProviderVehicle).filter(
        ProviderVehicle.id == vehicle_id,
        ProviderVehicle.provider_id == provider.id,
    ).first()
    if vehicle:
        db.delete(vehicle)
        db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle deleted.", status_code=303)


@router.post("/vehicles/{vehicle_id}/edit", response_class=HTMLResponse)
def edit_vehicle_submit(
    vehicle_id: int,
    request: Request,
    origin: Optional[str] = Form(None),
    destination: Optional[str] = Form(None),
    departure_time: Optional[str] = Form(None),
    arrival_time: Optional[str] = Form(None),
    fixed_fare_inr: Optional[float] = Form(None),
    price_per_km_inr: Optional[float] = Form(None),
    pickup_points: Optional[str] = Form(None),
    dropoff_points: Optional[str] = Form(None),
    service_dates: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    vehicle = db.query(ProviderVehicle).filter(
        ProviderVehicle.id == vehicle_id,
        ProviderVehicle.provider_id == provider.id,
    ).first()

    if vehicle:
        if origin is not None:
            vehicle.origin = origin
        if destination is not None:
            vehicle.destination = destination
        if departure_time is not None:
            vehicle.departure_time = departure_time if departure_time else None
        if arrival_time is not None:
            vehicle.arrival_time = arrival_time if arrival_time else None
        if fixed_fare_inr is not None:
            vehicle.fixed_fare_inr = fixed_fare_inr
        if price_per_km_inr is not None:
            vehicle.price_per_km_inr = price_per_km_inr
        
        vehicle.pickup_points = pickup_points if pickup_points else None
        vehicle.dropoff_points = dropoff_points if dropoff_points else None
        vehicle.service_dates = service_dates if service_dates else None

        db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle listing updated successfully!", status_code=303)



# ── Bookings ───────────────────────────────────────────────────────────────

@router.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()
    vehicle_ids = [v.id for v in vehicles]

    if vehicle_ids:
        db.query(ProviderBooking).filter(
            ProviderBooking.vehicle_id.in_(vehicle_ids),
            ProviderBooking.provider_unread == True
        ).update({ProviderBooking.provider_unread: False}, synchronize_session=False)
        db.commit()

    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id.in_(vehicle_ids)
    ).order_by(ProviderBooking.created_at.desc()).all() if vehicle_ids else []

    return templates.TemplateResponse(request, "provider_bookings.html", {
        "provider": provider,
        "bookings": bookings,
        "vehicles": vehicles,
        "has_unread_bookings": False,
    })


# ── Settings ───────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "provider_settings.html", {
        "provider": provider,
        "success": success,
        "has_unread_bookings": check_provider_unread_bookings(provider, db),
    })


@router.post("/settings", response_class=HTMLResponse)
def settings_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    alternate_email: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    service_type: str = Form(...),
    booking_mode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)
    if not provider.company_name:
        return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

    provider.company_name = company_name
    provider.contact_person = contact_person
    provider.phone = phone
    provider.alternate_email = alternate_email
    provider.city = city or ""
    provider.service_type = service_type
    provider.booking_mode = booking_mode
    db.commit()

    return RedirectResponse("/provider/settings?success=Settings updated successfully!", status_code=303)
