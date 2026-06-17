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
from app.models.models import Provider, ProviderVehicle, ProviderBooking
from app.provider.auth import (
    hash_password, verify_password,
    create_provider_token, get_provider_from_cookie,
)

router = APIRouter(prefix="/provider")
templates = Jinja2Templates(directory="templates")


# ── Register ───────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "provider_register.html", {})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),
    service_type: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(Provider).filter(Provider.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "provider_register.html", {
            "error": "Email already registered."
        })

    provider = Provider(
        company_name=company_name,
        contact_person=contact_person,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        city=city,
        service_type=service_type,
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


# ── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

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
    })


# ── Vehicles ───────────────────────────────────────────────────────────────

@router.get("/vehicles", response_class=HTMLResponse)
def vehicles_page(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    vehicles = db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()

    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "provider_vehicles.html", {
        "provider": provider,
        "vehicles": vehicles,
        "success": success,
    })


@router.post("/vehicles", response_class=HTMLResponse)
def add_vehicle_submit(
    request: Request,
    vehicle_type: str = Form(...),
    vehicle_name: str = Form(...),
    origin: str = Form(...),
    destination: str = Form(...),
    departure_time: Optional[str] = Form(None),
    total_seats: int = Form(...),
    fixed_fare_inr: Optional[float] = Form(None),
    price_per_km_inr: Optional[float] = Form(None),
    driver_included: str = Form("true"),
    db: Session = Depends(get_db),
):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    vehicle = ProviderVehicle(
        provider_id=provider.id,
        vehicle_type=vehicle_type,
        vehicle_name=vehicle_name,
        driver_included=(driver_included == "true"),
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        fixed_fare_inr=fixed_fare_inr,
        price_per_km_inr=price_per_km_inr,
        total_seats=total_seats,
    )
    db.add(vehicle)
    db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle added successfully!", status_code=303)


@router.post("/vehicles/{vehicle_id}/delete")
def delete_vehicle(vehicle_id: int, request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    vehicle = db.query(ProviderVehicle).filter(
        ProviderVehicle.id == vehicle_id,
        ProviderVehicle.provider_id == provider.id,
    ).first()
    if vehicle:
        db.delete(vehicle)
        db.commit()

    return RedirectResponse("/provider/vehicles?success=Vehicle deleted.", status_code=303)


# ── Bookings ───────────────────────────────────────────────────────────────

@router.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, db: Session = Depends(get_db)):
    provider = get_provider_from_cookie(request, db)
    if not provider:
        return RedirectResponse("/provider/login", status_code=303)

    vehicle_ids = [v.id for v in db.query(ProviderVehicle).filter(
        ProviderVehicle.provider_id == provider.id
    ).all()]

    bookings = db.query(ProviderBooking).filter(
        ProviderBooking.vehicle_id.in_(vehicle_ids)
    ).order_by(ProviderBooking.created_at.desc()).all() if vehicle_ids else []

    return templates.TemplateResponse(request, "provider_bookings.html", {
        "provider": provider,
        "bookings": bookings,
    })
