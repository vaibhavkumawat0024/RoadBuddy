import re
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from app.core.config import settings

DUFFEL_URL = "https://api.duffel.com"
DUFFEL_HEADERS = {
    "Duffel-Version": "v2",
    "Content-Type": "application/json"
}

# Cache for airport suggestions to save API calls
IATA_CACHE: Dict[str, str] = {
    "jaipur": "JAI",
    "delhi": "DEL",
    "mumbai": "BOM",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "kolkata": "CCU",
    "chennai": "MAA",
    "hyderabad": "HYD",
    "goa": "GOI",
    "udaipur": "UDR",
    "chandigarh": "IXC",
    "manali": "IXC",  # Chandigarh is closest major airport to Manali
    "agra": "AGR",
    "shimla": "SLV",
    "pune": "PNQ",
    "ahmedabad": "AMD",
    "jodhpur": "JDH",
    "jaisalmer": "JSA",
    "amritsar": "ATQ",
    "srinagar": "SXR",
    "leh": "IXL"
}

def get_auth_headers() -> Dict[str, str]:
    token = settings.duffel_api_key.strip() if settings.duffel_api_key else ""
    if not token:
        raise ValueError("DUFFEL_API_KEY environment variable is not configured. Please add it to your .env file.")
    headers = DUFFEL_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"
    return headers

def parse_iso_duration(dur_str: str) -> float:
    """Parse ISO 8601 duration (e.g. 'PT2H15M' or 'PT1H') to hours."""
    if not dur_str:
        return 2.0
    hours = 0.0
    minutes = 0.0
    h_match = re.search(r'(\d+)H', dur_str)
    m_match = re.search(r'(\d+)M', dur_str)
    if h_match:
        hours = float(h_match.group(1))
    if m_match:
        minutes = float(m_match.group(1))
    return round(hours + minutes / 60.0, 1)

async def resolve_iata_code(city_name: str) -> str:
    """Lookup city name to get IATA code using cache or suggestions API."""
    city_lower = city_name.strip().lower()
    if city_lower in IATA_CACHE:
        return IATA_CACHE[city_lower]

    # Query Duffel suggestion
    url = f"{DUFFEL_URL}/places/suggestions"
    params = {"query": city_name}
    headers = get_auth_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            suggestions = data.get("data", [])
            if suggestions:
                # Find first with IATA code
                for sug in suggestions:
                    iata = sug.get("iata_code")
                    if iata:
                        IATA_CACHE[city_lower] = iata
                        return iata
                # Fallback to suggestion ID if no IATA
                fallback_id = suggestions[0].get("id")
                if fallback_id:
                    IATA_CACHE[city_lower] = fallback_id
                    return fallback_id
        except Exception as e:
            print(f"Error suggesting IATA for city {city_name}: {e}")
            
    # Default fallbacks
    if "delhi" in city_lower: return "DEL"
    if "mumbai" in city_lower: return "BOM"
    if "jaipur" in city_lower: return "JAI"
    return "DEL"  # Absolute fallback to Delhi

async def geocode_city_coordinates(city_name: str) -> tuple[float, float]:
    """Geocode city name using Mapbox API or fallback to common Indian coordinates."""
    token = settings.mapbox_access_token.strip() if settings.mapbox_access_token else ""
    if token:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{city_name}.json"
        params = {
            "access_token": token,
            "limit": 1
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, params=params)
                res.raise_for_status()
                data = res.json()
                features = data.get("features", [])
                if features:
                    center = features[0].get("center")  # [lon, lat]
                    if center and len(center) == 2:
                        return center[1], center[0]
            except Exception as e:
                print(f"Mapbox geocoding failed for {city_name}: {e}")

    # Fallback coordinates mapping
    fallbacks = {
        "jaipur": (26.9124, 75.7873),
        "delhi": (28.6139, 77.2090),
        "new delhi": (28.6139, 77.2090),
        "mumbai": (19.0760, 72.8777),
        "bangalore": (12.9716, 77.5946),
        "bengaluru": (12.9716, 77.5946),
        "kolkata": (22.5726, 88.3639),
        "chennai": (13.0827, 80.2707),
        "hyderabad": (17.3850, 78.4867),
        "goa": (15.2993, 74.1240),
        "udaipur": (24.5854, 73.7125),
        "chandigarh": (30.7333, 76.7794),
        "manali": (32.2396, 77.1887),
        "agra": (27.1767, 78.0081),
        "shimla": (31.1048, 77.1734),
        "pune": (18.5204, 73.8567),
        "ahmedabad": (23.0225, 72.5714),
        "jodhpur": (26.2389, 73.0243),
        "jaisalmer": (26.9157, 70.9083),
        "amritsar": (31.6340, 74.8723),
        "srinagar": (34.0837, 74.7973),
        "leh": (34.1526, 77.5771)
    }
    
    clean = city_name.strip().lower()
    for k, coords in fallbacks.items():
        if k in clean or clean in k:
            return coords
            
    return 26.9124, 75.7873 # default to Jaipur coordinates

# ─── FLIGHTS API FUNCTIONS ───

async def search_flights(origin: str, destination: str, travel_date: str, num_seats: int, cabin_class: str = "economy") -> list[Dict[str, Any]]:
    """Create an offer request and return mapped flights/offers."""
    try:
        origin_iata = await resolve_iata_code(origin)
        dest_iata = await resolve_iata_code(destination)
    except Exception as e:
        raise ValueError(f"Could not resolve flight codes: {str(e)}")

    url = f"{DUFFEL_URL}/air/offer_requests"
    headers = get_auth_headers()
    
    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin_iata,
                    "destination": dest_iata,
                    "departure_date": travel_date
                }
            ],
            "passengers": [{"type": "adult"} for _ in range(num_seats)],
            "cabin_class": cabin_class
        }
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 422:
                # Handle parameter validation error
                err_data = res.json().get("errors", [{}])[0]
                detail = err_data.get("message", "Invalid flight search parameters")
                raise ValueError(detail)
            res.raise_for_status()
            response_data = res.json()
        except httpx.HTTPStatusError as e:
            err_msg = "Duffel search request failed"
            try:
                err_msg = e.response.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
        except Exception as e:
            raise RuntimeError(f"Flight search failed: {str(e)}")

    offers = response_data.get("data", {}).get("offers", [])
    results = []
    
    for offer in offers:
        slices = offer.get("slices", [])
        if not slices:
            continue
        slice_obj = slices[0]
        segments = slice_obj.get("segments", [])
        if not segments:
            continue
        first_seg = segments[0]
        last_seg = segments[-1]
        
        # Mapped flight attributes
        offer_id = offer.get("id")
        airline_name = offer.get("owner", {}).get("name", "Airline")
        carrier_iata = first_seg.get("marketing_carrier", {}).get("iata_code", "FL")
        flight_num = first_seg.get("marketing_carrier_flight_number", "100")
        flight_code = f"{carrier_iata} {flight_num}"
        
        # Extract time from Departing At
        dep_at = first_seg.get("departing_at", "")
        arr_at = last_seg.get("arriving_at", "")
        
        # Time strings formatting
        dep_time = dep_at.split("T")[-1][:5] if "T" in dep_at else "10:00"
        arr_time = arr_at.split("T")[-1][:5] if "T" in arr_at else "12:00"
        
        # Duration calculation
        duration_hrs = parse_iso_duration(slice_obj.get("duration", ""))
        
        # Price
        fare_inr = float(offer.get("total_amount", 5000.0))
        
        results.append({
            "id": f"flight_{offer_id}",  # prefix with flight_ for router routing
            "mode": "flight",
            "operator": airline_name,
            "airline": airline_name,
            "flight_number": flight_code,
            "origin": first_seg.get("origin", {}).get("name", origin_iata),
            "destination": last_seg.get("destination", {}).get("name", dest_iata),
            "departure_time": dep_time,
            "arrival_time": arr_time,
            "duration_hrs": duration_hrs,
            "fare_inr": fare_inr,
            "seats_available": 10,
            "travel_class": cabin_class.capitalize()
        })
        
    return results

async def get_offer(offer_id: str) -> Dict[str, Any]:
    """Retrieve an offer directly from Duffel to get fresh prices."""
    url = f"{DUFFEL_URL}/air/offers/{offer_id}"
    headers = get_auth_headers()
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("data", {})

async def create_flight_order(offer_id: str, passenger_details: List[Dict[str, Any]], amount: float, currency: str = "INR") -> Dict[str, Any]:
    """Re-fetches offer, builds passengers referencing offer passenger IDs, and creates order."""
    offer = await get_offer(offer_id)
    offer_passengers = offer.get("passengers", [])
    
    if len(offer_passengers) < len(passenger_details):
        raise ValueError("Flight offer does not support this many passengers.")
        
    passengers_payload = []
    
    for i, p_info in enumerate(passenger_details):
        offer_p = offer_passengers[i]
        
        # Parse passenger name
        full_name = p_info.get("name", "Traveler").strip()
        parts = full_name.split(" ", 1)
        given_name = parts[0]
        family_name = parts[1] if len(parts) > 1 else "Traveler"
        
        # Born on calculation
        age = 30
        try:
            age = int(p_info.get("age", 30))
        except ValueError:
            pass
        born_on = f"{2026 - age}-01-01"
        
        passengers_payload.append({
            "id": offer_p["id"],
            "given_name": given_name,
            "family_name": family_name,
            "gender": "u",
            "title": "mr",
            "born_on": born_on,
            "email": p_info.get("email", "passenger@example.com"),
            "phone_number": p_info.get("phone", "+919999999999")
        })
        
    url = f"{DUFFEL_URL}/air/orders"
    headers = get_auth_headers()
    
    payload = {
        "data": {
            "selected_offers": [offer_id],
            "passengers": passengers_payload,
            "payments": [
                {
                    "type": "balance",
                    "amount": offer.get("total_amount", str(amount)),
                    "currency": offer.get("total_currency", currency)
                }
            ]
        }
    }
    
    async with httpx.AsyncClient(timeout=45) as client:
        res = await client.post(url, headers=headers, json=payload)
        if res.status_code != 201:
            err_msg = "Failed to create Duffel order"
            try:
                err_msg = res.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
        return res.json().get("data", {})

async def get_flight_order(order_id: str) -> Dict[str, Any]:
    """Retrieve details of a flight order from Duffel."""
    url = f"{DUFFEL_URL}/air/orders/{order_id}"
    headers = get_auth_headers()
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("data", {})

async def cancel_flight_order(order_id: str) -> Dict[str, Any]:
    """Performs the full Duffel cancellation flow (quote cancellation -> confirm cancellation)."""
    headers = get_auth_headers()
    
    # 1. Create order cancellation quote
    quote_url = f"{DUFFEL_URL}/air/order_cancellations"
    quote_payload = {
        "data": {
            "order_id": order_id
        }
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(quote_url, headers=headers, json=quote_payload)
        if res.status_code != 201:
            err_msg = "Order cancellation is not supported or quote creation failed."
            try:
                err_msg = res.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
            
        cancellation = res.json().get("data", {})
        cancellation_id = cancellation.get("id")
        
        # 2. Confirm the cancellation
        confirm_url = f"{DUFFEL_URL}/air/order_cancellations/{cancellation_id}/actions/confirm"
        confirm_res = await client.post(confirm_url, headers=headers)
        if confirm_res.status_code != 200:
            err_msg = "Confirming cancellation failed"
            try:
                err_msg = confirm_res.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
            
        return confirm_res.json().get("data", {})

# ─── HOTELS/STAYS API FUNCTIONS ───

async def search_hotels(city: str, check_in: str, check_out: str, num_rooms: int = 1, num_guests: int = 1) -> list[Dict[str, Any]]:
    """Geocode city and perform stay search in Duffel Stays."""
    try:
        lat, lon = await geocode_city_coordinates(city)
    except Exception as e:
        raise ValueError(f"Could not geocode city {city}: {str(e)}")

    url = f"{DUFFEL_URL}/stays/search"
    headers = get_auth_headers()
    
    payload = {
        "data": {
            "location": {
                "geographic_coordinates": {
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": 20
            },
            "check_in_date": check_in,
            "check_out_date": check_out,
            "rooms": num_rooms,
            "guests": [{"type": "adult"} for _ in range(num_guests)]
        }
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            response_data = res.json()
        except httpx.HTTPStatusError as e:
            err_msg = "Duffel stays search failed"
            try:
                err_msg = e.response.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
        except Exception as e:
            raise RuntimeError(f"Hotel search failed: {str(e)}")

    results = response_data.get("data", {}).get("results", [])
    mapped_hotels = []
    
    # Calculate nights
    try:
        from datetime import datetime
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max((d2 - d1).days, 1)
    except Exception:
        nights = 1

    for res_item in results:
        search_result_id = res_item.get("id")
        acc = res_item.get("accommodation", {})
        if not acc:
            continue
            
        cheapest_amount = float(res_item.get("cheapest_rate_total_amount", 1000.0))
        # Compute price per night
        price_per_night = cheapest_amount / (nights * num_rooms)
        
        # Amenities list
        amenities = acc.get("amenities", [])
        amenities_str = ",".join(amenities[:4]) if amenities else "Air Conditioning,Wi-Fi,Room Service,Parking"
        
        mapped_hotels.append({
            "id": f"duffel_stay_{search_result_id}",  # Mapped search result ID
            "name": acc.get("name", "Luxury Resort & Stay"),
            "city": acc.get("location", {}).get("city", {}).get("name", city.capitalize()),
            "address": acc.get("location", {}).get("address", "Main Road, Center"),
            "star_rating": float(acc.get("rating", 4.0)),
            "price_per_night_inr": price_per_night,
            "rooms_available": 5,
            "amenities": amenities_str,
            "avg_rating": float(acc.get("rating", 4.0)),
            "total_reviews": 12,
            "accommodation_id": acc.get("id") # Keep local reference
        })
        
    return mapped_hotels

async def book_hotel(search_result_id: str, guest_details: Dict[str, Any], amount: float) -> Dict[str, Any]:
    """Fetch rates, quote cheapest rate, and book Stays reservation."""
    headers = get_auth_headers()
    
    # 1. Fetch rates
    rates_url = f"{DUFFEL_URL}/stays/search_results/{search_result_id}/actions/fetch_all_rates"
    
    async with httpx.AsyncClient(timeout=45) as client:
        rates_res = await client.post(rates_url, headers=headers, json={"data": {}})
        if rates_res.status_code != 200:
            raise RuntimeError("Hotel rates are no longer available. Please try a new search.")
            
        rates = rates_res.json().get("data", {}).get("rates", [])
        if not rates:
            raise RuntimeError("No available rooms/rates found for this accommodation.")
            
        # Select cheapest rate
        cheapest_rate = min(rates, key=lambda r: float(r.get("total_amount", 9999999)))
        rate_id = cheapest_rate["id"]
        
        # 2. Create Quote
        quote_url = f"{DUFFEL_URL}/stays/quotes"
        quote_payload = {
            "data": {
                "rate_id": rate_id
            }
        }
        quote_res = await client.post(quote_url, headers=headers, json=quote_payload)
        if quote_res.status_code != 201:
            raise RuntimeError("Selected room rate could not be quoted/verified.")
            
        quote = quote_res.json().get("data", {})
        quote_id = quote["id"]
        
        # 3. Create Stays Booking
        book_url = f"{DUFFEL_URL}/stays/bookings"
        
        # Format guest details
        lead_name = guest_details.get("passenger_name", "Traveler").strip()
        parts = lead_name.split(" ", 1)
        given_name = parts[0]
        family_name = parts[1] if len(parts) > 1 else "Traveler"
        
        # Phone check
        phone = guest_details.get("passenger_phone", "+919999999999")
        if not phone.startswith("+"):
            phone = "+91" + phone.replace(" ", "")
            
        guests_payload = [
            {
                "given_name": given_name,
                "family_name": family_name,
                "born_on": "1990-01-01"
            }
        ]
        
        booking_payload = {
            "data": {
                "quote_id": quote_id,
                "phone_number": phone,
                "email": guest_details.get("passenger_email", "guest@example.com"),
                "guests": guests_payload
            }
        }
        
        book_res = await client.post(book_url, headers=headers, json=booking_payload)
        if book_res.status_code != 201:
            err_msg = "Failed to complete hotel booking on Duffel"
            try:
                err_msg = book_res.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
            
        return book_res.json().get("data", {})

async def cancel_hotel_booking(duffel_booking_id: str) -> Dict[str, Any]:
    """Cancel stays booking directly on Duffel."""
    url = f"{DUFFEL_URL}/stays/bookings/{duffel_booking_id}/actions/cancel"
    headers = get_auth_headers()
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(url, headers=headers, json={"data": {}})
        if res.status_code != 200:
            err_msg = "Failed to cancel stays booking"
            try:
                err_msg = res.json().get("errors", [{}])[0].get("message", err_msg)
            except Exception:
                pass
            raise RuntimeError(err_msg)
        return res.json().get("data", {})
