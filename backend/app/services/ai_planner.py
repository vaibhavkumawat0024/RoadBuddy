"""
AI Trip Planner Service — RoadBuddy v2 (Groq)
----------------------------------------------
Powered by Groq API (free) with Llama 3 model.
"""

import json
import httpx
from datetime import date
from app.core.config import settings
from app.schemas.schemas import TripCreate, ItineraryStop, TripOut, TravelMode

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def get_season(start_date) -> str:
    try:
        if isinstance(start_date, str):
            month = int(start_date.split("-")[1])
        else:
            month = start_date.month
    except Exception:
        month = date.today().month
    if month in [3, 4, 5]:
        return "summer"
    elif month in [6, 7, 8, 9]:
        return "monsoon"
    else:
        return "winter"


def get_season_tips(season: str, destination: str) -> str:
    if season == "summer":
        return f"It is SUMMER. Advise travelling early morning before 9am. Carry extra water. Avoid 12pm-4pm driving."
    elif season == "monsoon":
        return f"It is MONSOON. Warn about slippery roads near {destination}. Check road status before travel."
    else:
        return f"It is WINTER. Suggest warm clothing. Warn about fog on highways early morning."


def get_group_tips(group_type: str, num_people: int) -> str:
    tips = {
        "family": f"FAMILY trip with {num_people} people. Add kid-friendly stops with clean restrooms every 100km. Max 4 hours driving per day.",
        "couple": "COUPLE trip. Suggest romantic viewpoints and sunset spots. Recommend boutique hotels.",
        "friends": f"FRIENDS trip with {num_people} people. Suggest adventure activities and street food spots.",
        "solo": "SOLO trip. Prioritise safety — suggest busy dhabas and well-lit stops.",
    }
    return tips.get(group_type, f"Group of {num_people} people.")


def get_budget_breakdown(budget_inr: float, num_people: int, fuel_type: str, travel_mode: str) -> str:
    per_person = budget_inr / max(num_people, 1)
    if travel_mode == "own_vehicle":
        fuel_pct = 0.30 if fuel_type != "electric" else 0.15
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person). "
            f"Split: Fuel Rs {budget_inr * fuel_pct:.0f}, Tolls Rs {budget_inr * 0.10:.0f}, "
            f"Hotels Rs {budget_inr * 0.30:.0f}, Food Rs {budget_inr * 0.20:.0f}."
        )
    else:
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person). "
            f"Split: Hotels Rs {budget_inr * 0.45:.0f}, Food Rs {budget_inr * 0.30:.0f}, Activities Rs {budget_inr * 0.25:.0f}."
        )


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    import math
    if not (lat1 and lon1 and lat2 and lon2):
        return 320.0
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    # Multiply by 1.3 to get realistic road distance (since roads are not straight lines)
    return round(distance * 1.3, 1)


def build_own_vehicle_prompt(trip: TripCreate, vehicle_info: dict) -> str:
    fuel_type = vehicle_info.get("fuel_type", "petrol")
    category  = vehicle_info.get("category", "car")
    mileage   = vehicle_info.get("mileage_kmpl", 15.0)
    season    = get_season(trip.start_date)
    
    lat1, lon1 = trip.origin_lat, trip.origin_lon
    lat2, lon2 = trip.destination_lat, trip.destination_lon
    dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    
    return f"""You are RoadBuddy AI, India's expert road trip planner.

Trip: {trip.origin} to {trip.destination} | {trip.start_date} to {trip.end_date}
Distance: Approximately {dist} km one-way (so total round-trip distance is {dist * 2} km).
Vehicle Selected by User: {category.upper()} running on {fuel_type.upper()} with an efficiency/mileage of {mileage} KMPL.
Season: {season.upper()}
{get_budget_breakdown(trip.budget_inr, trip.num_people, fuel_type, "own_vehicle")}
Group: {get_group_tips(trip.group_type, trip.num_people)}
Season tip: {get_season_tips(season, trip.destination)}

Generate a complete road trip covering GOING ROUTE, DESTINATION, and RETURN ROUTE.
IMPORTANT: Calculate the fuel cost based on:
1. Round-trip distance of {dist * 2} km.
2. Vehicle mileage of {mileage} KMPL.
3. Average fuel prices in India: Petrol (~104 INR/L), Diesel (~94 INR/L), CNG (~85 INR/L), Electric (Rs 2.5 per km).
Use real Indian town names and NH highway numbers.

Return ONLY valid JSON, no markdown:
{{
  "total_distance_km": {dist * 2},
  "fuel_cost_inr": 2400,
  "toll_cost_inr": 680,
  "return_toll_cost_inr": 680,
  "return_fuel_cost_inr": 2400,
  "hotel_cost_inr": 2500,
  "food_cost_inr": 1200,
  "total_estimated_cost_inr": 9860,
  "season": "{season}",
  "season_tip": "One key travel tip.",
  "ai_summary": "2-3 sentence trip summary.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "HP Petrol Pump, NH-48, Ajmer Road, Jaipur",
      "place_type": "fuel",
      "description": "Fill up before leaving.",
      "estimated_cost_inr": 2400,
      "highway": "NH-48",
      "lat": null,
      "lng": null
    }}
  ]
}}
Place types: going_route, fuel, food, hotel, sightseeing, destination_food, return_route, toll"""


def build_transport_prompt(trip: TripCreate) -> str:
    season = get_season(trip.start_date)
    return f"""You are RoadBuddy AI, India's expert trip planner.

Destination: {trip.destination} | {trip.start_date} to {trip.end_date}
Season: {season.upper()}
{get_budget_breakdown(trip.budget_inr, trip.num_people, "na", "public")}
Group: {get_group_tips(trip.group_type, trip.num_people)}

Generate destination-only itinerary. NO route/fuel/toll stops.
Use real place names. Realistic 2024-2025 INR prices.
Return ONLY valid JSON, no markdown:
{{
  "total_distance_km": 0,
  "hotel_cost_inr": 3000,
  "food_cost_inr": 1500,
  "total_estimated_cost_inr": 4500,
  "season": "{season}",
  "season_tip": "One key tip.",
  "ai_summary": "2-3 sentence summary.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "Hadimba Devi Temple, Manali",
      "place_type": "sightseeing",
      "description": "Ancient temple surrounded by cedar forest.",
      "estimated_cost_inr": 50,
      "highway": null,
      "lat": null,
      "lng": null
    }}
  ]
}}
Place types: sightseeing, hotel, destination_food"""


async def call_groq(prompt: str) -> dict:
    import asyncio
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(GROQ_URL, headers=headers, json=payload)
            if res.status_code == 429:
                wait = (attempt + 1) * 15
                print(f"Rate limit hit, waiting {wait}s...")
                await asyncio.sleep(wait)
                continue
            res.raise_for_status()
            text = res.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())

    # All retries failed
    raise RuntimeError("All Groq retry attempts failed.")


def mock_own_vehicle(trip: TripCreate, vehicle_info: dict = None) -> dict:
    season = get_season(trip.start_date)
    
    fuel_type = vehicle_info.get("fuel_type", "petrol") if vehicle_info else "petrol"
    category = vehicle_info.get("category", "car") if vehicle_info else "car"
    mileage_kmpl = vehicle_info.get("mileage_kmpl", 15.0) if vehicle_info else 15.0
    
    # Calculate road distance
    lat1, lon1 = trip.origin_lat, trip.origin_lon
    lat2, lon2 = trip.destination_lat, trip.destination_lon
    dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    
    # Calculate fuel cost one-way
    fuel_price = 105.0
    if fuel_type == "diesel":
        fuel_price = 90.0
    elif fuel_type == "cng":
        fuel_price = 85.0

    if fuel_type == "electric":
        if mileage_kmpl > 50:
            fuel_cost = (dist / mileage_kmpl) * 300.0
        else:
            fuel_cost = (dist / max(mileage_kmpl, 1.0)) * 8.0
    else:
        fuel_cost = (dist / max(mileage_kmpl, 1.0)) * fuel_price
        
    fuel_cost = round(fuel_cost, 2)
    return_fuel_cost = fuel_cost
    
    # Toll cost estimation based on distance (approx 1.5 INR per km for highways)
    toll_cost = round(dist * 1.5, 2)
    return_toll_cost = toll_cost
    
    # Hotel and food costs based on budget and duration
    hotel_cost = round(trip.budget_inr * 0.35, 2)
    food_cost = round(trip.budget_inr * 0.20, 2)
    
    total_est = round(fuel_cost + return_fuel_cost + toll_cost + return_toll_cost + hotel_cost + food_cost, 2)
    
    stops = [
        {"day": 1, "time_slot": "morning", "place_name": f"HP Petrol Pump, NH-48, {trip.origin}",
         "place_type": "fuel", "description": f"Fill up your {fuel_type} vehicle.", "estimated_cost_inr": fuel_cost, "highway": "NH-48", "lat": None, "lng": None},
        {"day": 1, "time_slot": "afternoon", "place_name": "Apna Dhaba — Highway Lunch",
         "place_type": "food", "description": "Popular highway dhaba.", "estimated_cost_inr": 400, "highway": "NH-48", "lat": None, "lng": None},
        {"day": 1, "time_slot": "evening", "place_name": f"Hotel Shree Palace, {trip.destination}",
         "place_type": "hotel", "description": "Confirmed stay at destination.", "estimated_cost_inr": hotel_cost, "highway": None, "lat": None, "lng": None},
        {"day": 2, "time_slot": "morning", "place_name": f"Main Attraction, {trip.destination}",
         "place_type": "sightseeing", "description": "Top must-visit attraction.", "estimated_cost_inr": 200, "highway": None, "lat": None, "lng": None},
        {"day": 3, "time_slot": "morning", "place_name": f"Indian Oil Pump, {trip.destination}",
         "place_type": "fuel", "description": "Fill up before heading back.", "estimated_cost_inr": return_fuel_cost, "highway": None, "lat": None, "lng": None},
        {"day": 3, "time_slot": "evening", "place_name": f"Home — {trip.origin}",
         "place_type": "return_route", "description": "Trip complete! Welcome home.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None},
    ]
    
    return {
        "total_distance_km": dist * 2,
        "fuel_cost_inr": fuel_cost,
        "toll_cost_inr": toll_cost,
        "return_fuel_cost_inr": return_fuel_cost,
        "return_toll_cost_inr": return_toll_cost,
        "hotel_cost_inr": hotel_cost,
        "food_cost_inr": food_cost,
        "total_estimated_cost_inr": total_est,
        "season": season,
        "season_tip": "Check road conditions and tyre pressure before leaving.",
        "ai_summary": f"A customized road trip from {trip.origin} to {trip.destination} in your {fuel_type} {category} (Mileage: {mileage_kmpl} KMPL).",
        "stops": stops
    }


def mock_transport_itinerary(trip: TripCreate) -> dict:
    season = get_season(trip.start_date)
    return {
        "total_distance_km": 0, "hotel_cost_inr": 3000, "food_cost_inr": 1500,
        "total_estimated_cost_inr": round(trip.budget_inr * 0.75, 2),
        "season": season, "season_tip": "Carry appropriate clothing.",
        "ai_summary": f"Explore the beautiful {trip.destination}.",
        "stops": [
            {"day": 1, "time_slot": "morning", "place_name": f"Top Attraction, {trip.destination}",
             "place_type": "sightseeing", "description": "Must-visit iconic spot.", "estimated_cost_inr": 200, "highway": None, "lat": None, "lng": None},
            {"day": 1, "time_slot": "afternoon", "place_name": "Local Food Street",
             "place_type": "destination_food", "description": "Best local street food.", "estimated_cost_inr": 400, "highway": None, "lat": None, "lng": None},
            {"day": 1, "time_slot": "evening", "place_name": "Hotel Grand Inn",
             "place_type": "hotel", "description": "Comfortable stay near city centre.", "estimated_cost_inr": 1500, "highway": None, "lat": None, "lng": None},
        ],
    }


async def generate_itinerary(trip: TripCreate, vehicle_info: dict) -> TripOut:
    try:
        if trip.travel_mode == TravelMode.own_vehicle:
            if settings.groq_api_key:
                try:
                    data = await call_groq(build_own_vehicle_prompt(trip, vehicle_info))
                except Exception as e:
                    print(f"Groq itinerary failed: {e}. Falling back to mock.")
                    data = mock_own_vehicle(trip, vehicle_info)
            else:
                data = mock_own_vehicle(trip, vehicle_info)
        else:
            if settings.groq_api_key:
                try:
                    data = await call_groq(build_transport_prompt(trip))
                except Exception as e:
                    print(f"Groq itinerary failed: {e}. Falling back to mock.")
                    data = mock_transport_itinerary(trip)
            else:
                data = mock_transport_itinerary(trip)

        stops = [ItineraryStop(**s) for s in data["stops"]]
        import uuid
        trip_uuid = uuid.uuid4().hex[:6]
        trip_id = f"trip_{trip.origin[:3].lower()}{trip.destination[:3].lower()}_{trip_uuid}"
        
        fuel_cost = data.get("fuel_cost_inr", 0) + data.get("return_fuel_cost_inr", 0)
        
        return TripOut(
            id=trip_id,
            origin=trip.origin, destination=trip.destination, travel_mode=trip.travel_mode,
            total_distance_km=data.get("total_distance_km", 0), stops=stops,
            fuel_cost_inr=fuel_cost,
            toll_cost_inr=data.get("toll_cost_inr", 0) + data.get("return_toll_cost_inr", 0),
            transport_fare_inr=0, return_fare_inr=0,
            hotel_cost_inr=data.get("hotel_cost_inr", 0),
            food_cost_inr=data.get("food_cost_inr", 0),
            total_estimated_cost_inr=data.get("total_estimated_cost_inr", 0),
            ai_summary=data.get("ai_summary", ""),
        )
    except Exception as e:
        raise RuntimeError(f"Itinerary generation failed: {e}") from e