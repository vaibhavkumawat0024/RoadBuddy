"""
Thin wrapper around httpx for calling the RoadBuddy backend API.
"""
import httpx
from app.core.config import BACKEND_URL


class BackendError(Exception):
    """Raised when the backend returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def _request(method: str, path: str, **kwargs):
    url = f"{BACKEND_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise BackendError(503, f"Backend connection failed: {exc}")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise BackendError(resp.status_code, detail)
    if resp.content:
        try:
            return resp.json()
        except Exception:
            return resp.text
    return None


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth & Profile ──────────────────────────────────────────────────────────

async def register_user(name: str, email: str, password: str):
    """Calls backend POST /api/users/register — triggers OTP email."""
    return await _request(
        "POST",
        "/api/users/register",
        json={"name": name, "email": email, "password": password},
    )


async def verify_otp(email: str, otp: str):
    """Calls backend POST /api/users/verify-otp."""
    return await _request(
        "POST",
        "/api/users/verify-otp",
        json={"email": email, "otp": otp},
    )


async def login_user(email: str, password: str):
    """Calls backend POST /api/users/login — OAuth2PasswordRequestForm expects form-encoded username/password."""
    return await _request(
        "POST",
        "/api/users/login",
        data={"username": email, "password": password},
    )


async def get_profile(token: str):
    """Calls backend GET /api/users/me — requires Bearer token."""
    return await _request("GET", "/api/users/me", headers=_auth_headers(token))


async def update_profile(token: str, name: str | None = None, email: str | None = None):
    """Calls backend PATCH /api/users/me — requires Bearer token."""
    payload = {}
    if name is not None:
        payload["name"] = name
    if email is not None:
        payload["email"] = email
    return await _request(
        "PATCH", "/api/users/me", json=payload, headers=_auth_headers(token)
    )


async def change_password(token: str, current_password: str, new_password: str):
    """Calls backend POST /api/users/change-password — requires Bearer token."""
    return await _request(
        "POST",
        "/api/users/change-password",
        json={"current_password": current_password, "new_password": new_password},
        headers=_auth_headers(token),
    )


# ── Vehicles ──────────────────────────────────────────────────────────────────

async def list_vehicles(token: str):
    """Calls backend GET /api/users/vehicles — requires Bearer token."""
    return await _request("GET", "/api/users/vehicles", headers=_auth_headers(token))


async def add_vehicle(token: str, payload: dict):
    """Calls backend POST /api/users/vehicles — requires Bearer token."""
    return await _request(
        "POST", "/api/users/vehicles", json=payload, headers=_auth_headers(token)
    )


async def delete_vehicle(token: str, vehicle_id: str):
    """Calls backend DELETE /api/users/vehicles/{vehicle_id} — requires Bearer token."""
    return await _request(
        "DELETE", f"/api/users/vehicles/{vehicle_id}", headers=_auth_headers(token)
    )


# ── Trips ─────────────────────────────────────────────────────────────────────

async def trip_chat(message: str, history: list, token: str = None):
    headers = _auth_headers(token) if token else {}
    return await _request(
        "POST", "/api/trips/chat", json={"message": message, "history": history}, headers=headers
    )


async def suggest_waypoints(origin: str, destination: str, preferences: list):
    return await _request(
        "POST",
        "/api/trips/suggest-waypoints",
        json={"origin": origin, "destination": destination, "preferences": preferences},
    )


async def safety_check(origin: str, destination: str, travel_date: str):
    return await _request(
        "POST",
        "/api/trips/safety-check",
        json={"origin": origin, "destination": destination, "travel_date": travel_date},
    )


async def trip_recommendations(home_city: str, budget_inr: float, interests: list):
    return await _request(
        "POST",
        "/api/trips/recommendations",
        json={"home_city": home_city, "budget_inr": budget_inr, "interests": interests},
    )


async def generate_trip(token: str, payload: dict):
    """Calls backend POST /api/trips/generate — requires Bearer token."""
    return await _request(
        "POST", "/api/trips/generate", json=payload, headers=_auth_headers(token)
    )


async def list_my_trips(token: str):
    """Calls backend GET /api/trips/my — requires Bearer token."""
    return await _request("GET", "/api/trips/my", headers=_auth_headers(token))


async def delete_trip(token: str, trip_id: str):
    """Calls backend DELETE /api/trips/{trip_id} — requires Bearer token."""
    return await _request(
        "DELETE", f"/api/trips/{trip_id}", headers=_auth_headers(token)
    )


async def get_trip(token: str, trip_id: str):
    """Calls backend GET /api/trips/{trip_id} — requires Bearer token."""
    return await _request(
        "GET", f"/api/trips/{trip_id}", headers=_auth_headers(token)
    )


# ── Community ─────────────────────────────────────────────────────────────────

async def browse_community_routes(tag: str | None = None, min_rating: float = 0.0, limit: int = 20):
    params = {"min_rating": min_rating, "limit": limit}
    if tag:
        params["tag"] = tag
    return await _request("GET", "/api/community/routes", params=params)


async def get_community_route(route_id: str):
    return await _request("GET", f"/api/community/routes/{route_id}")


async def publish_route(token: str, payload: dict):
    return await _request(
        "POST", "/api/community/routes", json=payload, headers=_auth_headers(token)
    )


async def clone_route(token: str, route_id: str):
    return await _request(
        "POST", f"/api/community/routes/{route_id}/clone", headers=_auth_headers(token)
    )


async def add_review(token: str, route_id: str, payload: dict):
    return await _request(
        "POST", f"/api/community/routes/{route_id}/review", json=payload, headers=_auth_headers(token)
    )


async def get_reviews(route_id: str):
    return await _request("GET", f"/api/community/routes/{route_id}/reviews")


async def smart_search(query: str):
    return await _request("POST", "/api/community/smart-search", json={"query": query})


# ── Fuel & Toll ───────────────────────────────────────────────────────────────

async def calculate_fuel(token: str, payload: dict):
    return await _request(
        "POST", "/api/fuel/calculate", json=payload, headers=_auth_headers(token)
    )


async def get_fuel_prices():
    return await _request("GET", "/api/fuel/fuel-prices")


async def get_toll_estimate(origin: str, destination: str, vehicle_category: str = "car"):
    params = {"origin": origin, "destination": destination, "vehicle_category": vehicle_category}
    return await _request("GET", "/api/fuel/toll-estimate", params=params)


# ── Journal ───────────────────────────────────────────────────────────────────

async def add_journal_entry(token: str, payload: dict):
    return await _request(
        "POST", "/api/journal/entry", json=payload, headers=_auth_headers(token)
    )


async def get_journal(token: str, trip_id: str):
    return await _request("GET", f"/api/journal/{trip_id}", headers=_auth_headers(token))


async def publish_journal(token: str, trip_id: str):
    return await _request(
        "PATCH", f"/api/journal/{trip_id}/publish", headers=_auth_headers(token)
    )


async def get_journal_summary(token: str, trip_id: str):
    return await _request("GET", f"/api/journal/{trip_id}/summary", headers=_auth_headers(token))


async def summarize_journal(payload: dict):
    return await _request("POST", "/api/journal/summarize", json=payload)


# ── Transport ─────────────────────────────────────────────────────────────────

async def search_transport(token: str, payload: dict):
    return await _request(
        "POST", "/api/transport/search", json=payload, headers=_auth_headers(token)
    )


async def book_transport(token: str, payload: dict):
    return await _request(
        "POST", "/api/transport/book", json=payload, headers=_auth_headers(token)
    )


async def list_bookings(token: str):
    return await _request("GET", "/api/transport/bookings", headers=_auth_headers(token))


async def cancel_booking(token: str, booking_id: str):
    return await _request(
        "PATCH", f"/api/transport/bookings/{booking_id}/cancel", headers=_auth_headers(token)
    )


# ── Travel Booking (Hotels/Trains/Buses/Flights) ───────────────────────────────

async def search_hotels(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/hotels/search", json=payload, headers=_auth_headers(token)
    )


async def book_hotel(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/hotels/book", json=payload, headers=_auth_headers(token)
    )


async def cancel_hotel_booking(token: str, booking_id: int):
    return await _request(
        "POST", f"/cancel-hotel-booking/{booking_id}", headers=_auth_headers(token)
    )


async def search_trains(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/trains/search", json=payload, headers=_auth_headers(token)
    )


async def book_train(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/trains/book", json=payload, headers=_auth_headers(token)
    )


async def search_buses(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/buses/search", json=payload, headers=_auth_headers(token)
    )


async def book_bus(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/buses/book", json=payload, headers=_auth_headers(token)
    )


async def search_flights(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/flights/search", json=payload, headers=_auth_headers(token)
    )


async def book_flight(token: str, payload: dict):
    return await _request(
        "POST", "/api/booking/flights/book", json=payload, headers=_auth_headers(token)
    )


# ── Traveler Provider Bookings ───────────────────────────────────────────────

async def list_provider_bookings(token: str):
    """Calls backend GET /api/provider/bookings/user — requires Bearer token."""
    return await _request("GET", "/api/provider/bookings/user", headers=_auth_headers(token))


async def cancel_provider_booking(token: str, booking_id: int):
    """Calls backend POST /api/provider/bookings/{booking_id}/cancel — requires Bearer token."""
    return await _request(
        "POST", f"/api/provider/bookings/{booking_id}/cancel", headers=_auth_headers(token)
    )


async def list_active_enroute_bookings(token: str, user_id: int):
    """Calls backend GET /api/provider/bookings/active-enroute?user_id=... — requires Bearer token."""
    return await _request(
        "GET", f"/api/provider/bookings/active-enroute?user_id={user_id}", headers=_auth_headers(token)
    )


async def track_provider_booking(token: str, booking_id: int):
    """Calls backend GET /api/provider/bookings/{booking_id}/track — requires Bearer token."""
    return await _request(
        "GET", f"/api/provider/bookings/{booking_id}/track", headers=_auth_headers(token)
    )


async def check_unread_provider_bookings(token: str):
    """Calls backend GET /api/provider/bookings/unread-check — requires Bearer token."""
    return await _request("GET", "/api/provider/bookings/unread-check", headers=_auth_headers(token))


async def mark_unread_provider_bookings_as_read(token: str):
    """Calls backend POST /api/provider/bookings/mark-read — requires Bearer token."""
    return await _request("POST", "/api/provider/bookings/mark-read", headers=_auth_headers(token))


async def list_cab_services(origin: str | None = None, destination: str | None = None):
    """Calls backend GET /api/provider/services."""
    params = {}
    if origin:
        params["origin"] = origin
    if destination:
        params["destination"] = destination
    return await _request("GET", "/api/provider/services", params=params)


# ── Provider Management API Client Calls ──────────────────────────────────────

async def register_provider(payload: dict):
    """Calls backend POST /api/provider/register"""
    return await _request("POST", "/api/provider/register", json=payload)


async def login_provider(payload: dict):
    """Calls backend POST /api/provider/login"""
    return await _request("POST", "/api/provider/login", json=payload)


async def get_provider_profile(token: str):
    """Calls backend GET /api/provider/me"""
    return await _request("GET", "/api/provider/me", headers=_auth_headers(token))


async def update_provider_profile(token: str, payload: dict):
    """Calls backend PATCH /api/provider/me"""
    return await _request("PATCH", "/api/provider/me", json=payload, headers=_auth_headers(token))


async def list_provider_vehicle_assets(token: str):
    """Calls backend GET /api/provider/vehicle-assets"""
    return await _request("GET", "/api/provider/vehicle-assets", headers=_auth_headers(token))


async def add_provider_vehicle_asset(token: str, payload: dict):
    """Calls backend POST /api/provider/vehicle-assets"""
    return await _request("POST", "/api/provider/vehicle-assets", json=payload, headers=_auth_headers(token))


async def delete_provider_vehicle_asset(token: str, asset_id: int):
    """Calls backend DELETE /api/provider/vehicle-assets/{asset_id}"""
    return await _request("DELETE", f"/api/provider/vehicle-assets/{asset_id}", headers=_auth_headers(token))


async def list_provider_vehicles(token: str):
    """Calls backend GET /api/provider/vehicles"""
    return await _request("GET", "/api/provider/vehicles", headers=_auth_headers(token))


async def add_provider_vehicle(token: str, payload: dict):
    """Calls backend POST /api/provider/vehicles"""
    return await _request("POST", "/api/provider/vehicles", json=payload, headers=_auth_headers(token))


async def delete_provider_vehicle(token: str, vehicle_id: int):
    """Calls backend DELETE /api/provider/vehicles/{vehicle_id}"""
    return await _request("DELETE", f"/api/provider/vehicles/{vehicle_id}", headers=_auth_headers(token))


async def list_provider_bookings_all(token: str):
    """Calls backend GET /api/provider/bookings (provider side)"""
    return await _request("GET", "/api/provider/bookings", headers=_auth_headers(token))


async def start_provider_booking_nav(token: str, booking_id: int):
    """Calls backend POST /api/provider/bookings/{booking_id}/start-nav"""
    return await _request("POST", f"/api/provider/bookings/{booking_id}/start-nav", headers=_auth_headers(token))


async def update_provider_booking_location(token: str, booking_id: int, lat: float, lon: float):
    """Calls backend POST /api/provider/bookings/{booking_id}/location"""
    return await _request(
        "POST",
        f"/api/provider/bookings/{booking_id}/location",
        json={"lat": lat, "lon": lon},
        headers=_auth_headers(token),
    )


async def start_provider_vehicle_trip(token: str, vehicle_id: int):
    """Calls backend POST /api/provider/vehicles/{vehicle_id}/start-trip"""
    return await _request("POST", f"/api/provider/vehicles/{vehicle_id}/start-trip", headers=_auth_headers(token))


async def update_provider_vehicle_location(token: str, vehicle_id: int, lat: float, lon: float):
    """Calls backend POST /api/provider/vehicles/{vehicle_id}/location"""
    return await _request(
        "POST",
        f"/api/provider/vehicles/{vehicle_id}/location",
        json={"lat": lat, "lon": lon},
        headers=_auth_headers(token),
    )


# ── Food & Restaurant API Client Methods ────────────────────────────────────────

async def get_restaurants(token: str, city: str):
    return await _request("GET", f"/api/food/restaurants?city={city}", headers=_auth_headers(token))

async def get_restaurant_menu(token: str, restaurant_id: int):
    return await _request("GET", f"/api/food/restaurants/{restaurant_id}/menu", headers=_auth_headers(token))

async def create_food_order(token: str, payload: dict):
    return await _request("POST", "/api/food/orders", json=payload, headers=_auth_headers(token))

async def update_food_order_arrival(token: str, order_id: int, payload: dict):
    return await _request("POST", f"/api/food/orders/{order_id}/arrival", json=payload, headers=_auth_headers(token))

async def add_menu_item_review(token: str, item_id: int, payload: dict):
    return await _request("POST", f"/api/food/menu-items/{item_id}/review", json=payload, headers=_auth_headers(token))

async def get_my_food_orders(token: str):
    return await _request("GET", "/api/food/my-orders", headers=_auth_headers(token))

# Provider-specific food methods:
async def get_provider_food_orders(token: str):
    return await _request("GET", "/api/food/provider/orders", headers=_auth_headers(token))

async def update_provider_food_order_status(token: str, order_id: int, status: str):
    return await _request("PATCH", f"/api/food/provider/orders/{order_id}/status", json={"status": status}, headers=_auth_headers(token))

async def update_provider_food_order_prep_time(token: str, order_id: int, prep_time_mins: int):
    return await _request("PATCH", f"/api/food/provider/orders/{order_id}/prep-time", json={"prep_time_mins": prep_time_mins}, headers=_auth_headers(token))

async def add_provider_menu_item(token: str, payload: dict):
    return await _request("POST", "/api/food/provider/menu", json=payload, headers=_auth_headers(token))

async def delete_provider_menu_item(token: str, item_id: int):
    return await _request("DELETE", f"/api/food/provider/menu/{item_id}", headers=_auth_headers(token))
