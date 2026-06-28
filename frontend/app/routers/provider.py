from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import urllib.parse

from app.core import api_client

router = APIRouter(prefix="/provider")
templates = Jinja2Templates(directory="app/templates")

PROVIDER_COOKIE_NAME = "provider_access_token"

def get_provider_token(request: Request) -> Optional[str]:
    return request.cookies.get(PROVIDER_COOKIE_NAME)


# ── Register & Login ─────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "provider_register.html", {"request": request, "error": None})


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    company_name: str = Form(""),
    contact_person: str = Form(""),
    phone: str = Form(""),
    city: str = Form(""),
    service_type: str = Form("car_rental"),
):
    payload = {
        "company_name": company_name,
        "contact_person": contact_person,
        "email": email,
        "password": password,
        "phone": phone,
        "city": city,
        "service_type": service_type
    }
    try:
        await api_client.register_provider(payload)
    except api_client.BackendError as e:
        return templates.TemplateResponse(request, "provider_register.html", {"request": request, "error": e.detail})
    
    return RedirectResponse(url="/provider/login?success=Registration successful! Please login.", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    return templates.TemplateResponse(request, "provider_login.html", {"request": request, "success": success, "error": error})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        data = await api_client.login_provider({"email": email, "password": password})
    except api_client.BackendError as e:
        return templates.TemplateResponse(request, "provider_login.html", {"request": request, "error": e.detail, "success": None})

    token = data.get("access_token")
    response = RedirectResponse(url="/provider/dashboard", status_code=303)
    if token:
        response.set_cookie(
            key=PROVIDER_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24, # 24h
        )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/provider/login", status_code=303)
    response.delete_cookie(PROVIDER_COOKIE_NAME)
    return response


# ── Dashboard & First-Time Setup ──────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        provider = await api_client.get_provider_profile(token)
        vehicles = await api_client.list_provider_vehicles(token)
        bookings = await api_client.list_provider_bookings_all(token)
    except api_client.BackendError:
        return RedirectResponse("/provider/login?error=Session expired. Please login again.", status_code=303)

    show_setup = not provider.get("company_name")
    total_revenue = sum(b.get("total_fare_inr", 0.0) for b in bookings)
    total_seats_booked = sum(b.get("num_seats", 0) for b in bookings)

    setup_required = request.query_params.get("setup_required")
    error = "Please complete your business profile setup first." if setup_required else None

    return templates.TemplateResponse(request, "provider_dashboard.html", {
        "request": request,
        "provider": provider,
        "vehicles": vehicles,
        "vehicle_count": len(vehicles),
        "total_bookings": len(bookings),
        "total_seats_booked": total_seats_booked,
        "total_revenue": total_revenue,
        "show_setup": show_setup,
        "error": error
    })


@router.post("/setup")
async def setup_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    alternate_email: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    service_type: str = Form(...),
    booking_mode: Optional[str] = Form(None),
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    payload = {
        "company_name": company_name,
        "contact_person": contact_person,
        "phone": phone,
        "alternate_email": alternate_email,
        "city": city or "",
        "service_type": service_type,
        "booking_mode": booking_mode
    }
    try:
        await api_client.update_provider_profile(token, payload)
    except api_client.BackendError:
        return RedirectResponse("/provider/login?error=Session expired.", status_code=303)

    return RedirectResponse("/provider/dashboard", status_code=303)


# ── Fleet & Listings Management ───────────────────────────────────────────────

@router.get("/vehicles", response_class=HTMLResponse)
async def vehicles_page(request: Request):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        provider = await api_client.get_provider_profile(token)
        if not provider.get("company_name"):
            return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

        vehicles = await api_client.list_provider_vehicles(token)
        vehicle_assets = await api_client.list_provider_vehicle_assets(token)
    except api_client.BackendError:
        return RedirectResponse("/provider/login?error=Session expired.", status_code=303)

    success = request.query_params.get("success")

    return templates.TemplateResponse(request, "provider_vehicles.html", {
        "request": request,
        "provider": provider,
        "vehicles": vehicles,
        "vehicle_assets": vehicle_assets,
        "success": success,
    })


@router.post("/vehicle-assets")
async def add_vehicle_asset_submit(
    request: Request,
    vehicle_type: str = Form(...),
    vehicle_name: str = Form(...),
    total_seats: int = Form(...),
    driver_included: str = Form("true"),
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    payload = {
        "vehicle_type": vehicle_type,
        "vehicle_name": vehicle_name,
        "total_seats": total_seats,
        "driver_included": (driver_included == "true")
    }
    try:
        await api_client.add_provider_vehicle_asset(token, payload)
    except api_client.BackendError as e:
        return RedirectResponse(f"/provider/vehicles?error={urllib.parse.quote(e.detail)}", status_code=303)

    return RedirectResponse("/provider/vehicles?success=Vehicle added to fleet successfully!", status_code=303)


@router.post("/vehicle-assets/{asset_id}/delete")
async def delete_vehicle_asset_submit(
    asset_id: int,
    request: Request,
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        await api_client.delete_provider_vehicle_asset(token, asset_id)
    except api_client.BackendError as e:
        return RedirectResponse(f"/provider/vehicles?error={urllib.parse.quote(e.detail)}", status_code=303)

    return RedirectResponse("/provider/vehicles?success=Vehicle deleted from fleet.", status_code=303)


@router.post("/vehicles")
async def add_vehicle_submit(
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
    vehicle_asset_id: Optional[int] = Form(None),
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    payload = {
        "vehicle_type": vehicle_type,
        "vehicle_name": vehicle_name,
        "driver_included": (driver_included == "true"),
        "origin": origin or "Unknown",
        "destination": destination or "Private",
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "total_seats": total_seats or 4,
        "fixed_fare_inr": fixed_fare_inr,
        "price_per_km_inr": price_per_km_inr,
        "pickup_points": pickup_points,
        "dropoff_points": dropoff_points,
        "vehicle_asset_id": vehicle_asset_id,
    }
    try:
        await api_client.add_provider_vehicle(token, payload)
    except api_client.BackendError as e:
        return RedirectResponse(f"/provider/vehicles?error={urllib.parse.quote(e.detail)}", status_code=303)

    return RedirectResponse("/provider/vehicles?success=Vehicle listing added successfully!", status_code=303)


@router.post("/vehicles/{vehicle_id}/delete")
async def delete_vehicle(
    vehicle_id: int,
    request: Request,
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        await api_client.delete_provider_vehicle(token, vehicle_id)
    except api_client.BackendError as e:
        return RedirectResponse(f"/provider/vehicles?error={urllib.parse.quote(e.detail)}", status_code=303)

    return RedirectResponse("/provider/vehicles?success=Vehicle deleted.", status_code=303)


# ── Customer Bookings & Dispatch ──────────────────────────────────────────────

@router.get("/bookings", response_class=HTMLResponse)
async def bookings_page(request: Request):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        provider = await api_client.get_provider_profile(token)
        if not provider.get("company_name"):
            return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)

        bookings = await api_client.list_provider_bookings_all(token)
        vehicles = await api_client.list_provider_vehicles(token)
    except api_client.BackendError:
        return RedirectResponse("/provider/login?error=Session expired.", status_code=303)

    return templates.TemplateResponse(request, "provider_bookings.html", {
        "request": request,
        "provider": provider,
        "bookings": bookings,
        "vehicles": vehicles,
    })


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    try:
        provider = await api_client.get_provider_profile(token)
        if not provider.get("company_name"):
            return RedirectResponse("/provider/dashboard?setup_required=1", status_code=303)
    except api_client.BackendError:
        return RedirectResponse("/provider/login?error=Session expired.", status_code=303)

    success = request.query_params.get("success")

    return templates.TemplateResponse(request, "provider_settings.html", {
        "request": request,
        "provider": provider,
        "success": success,
    })


@router.post("/settings")
async def settings_submit(
    request: Request,
    company_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    alternate_email: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    service_type: str = Form(...),
    booking_mode: Optional[str] = Form(None),
):
    token = get_provider_token(request)
    if not token:
        return RedirectResponse("/provider/login", status_code=303)

    payload = {
        "company_name": company_name,
        "contact_person": contact_person,
        "phone": phone,
        "alternate_email": alternate_email,
        "city": city or "",
        "service_type": service_type,
        "booking_mode": booking_mode
    }
    try:
        await api_client.update_provider_profile(token, payload)
    except api_client.BackendError as e:
        return RedirectResponse(f"/provider/settings?error={urllib.parse.quote(e.detail)}", status_code=303)

    return RedirectResponse("/provider/settings?success=Settings updated successfully!", status_code=303)


# ── Live Tracking API Proxy Endpoints ─────────────────────────────────────────

@router.post("/bookings/{booking_id}/start-nav")
async def proxy_start_booking_nav(booking_id: int, request: Request):
    token = get_provider_token(request)
    if not token:
        return {"status": "error", "message": "Unauthorized"}
    try:
        return await api_client.start_provider_booking_nav(token, booking_id)
    except api_client.BackendError as e:
        return {"status": "error", "message": e.detail}


@router.post("/bookings/{booking_id}/location")
async def proxy_update_booking_location(booking_id: int, request: Request):
    token = get_provider_token(request)
    if not token:
        return {"status": "error", "message": "Unauthorized"}
    try:
        body = await request.json()
        lat = body.get("lat")
        lon = body.get("lon")
        return await api_client.update_provider_booking_location(token, booking_id, lat, lon)
    except api_client.BackendError as e:
        return {"status": "error", "message": e.detail}


@router.post("/vehicles/{vehicle_id}/start-trip")
async def proxy_start_vehicle_trip(vehicle_id: int, request: Request):
    token = get_provider_token(request)
    if not token:
        return {"status": "error", "message": "Unauthorized"}
    try:
        return await api_client.start_provider_vehicle_trip(token, vehicle_id)
    except api_client.BackendError as e:
        return {"status": "error", "message": e.detail}


@router.post("/vehicles/{vehicle_id}/location")
async def proxy_update_vehicle_location(vehicle_id: int, request: Request):
    token = get_provider_token(request)
    if not token:
        return {"status": "error", "message": "Unauthorized"}
    try:
        body = await request.json()
        lat = body.get("lat")
        lon = body.get("lon")
        return await api_client.update_provider_vehicle_location(token, vehicle_id, lat, lon)
    except api_client.BackendError as e:
        return {"status": "error", "message": e.detail}


@router.get("/api/bookings")
async def get_provider_bookings_json(request: Request):
    token = get_provider_token(request)
    if not token:
        return []
    try:
        return await api_client.list_provider_bookings_all(token)
    except Exception:
        return []


@router.get("/api/vehicles")
async def get_provider_vehicles_json(request: Request):
    token = get_provider_token(request)
    if not token:
        return []
    try:
        return await api_client.list_provider_vehicles(token)
    except Exception:
        return []
