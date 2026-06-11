"""
AI Trip Planner Service
-----------------------
Two separate prompts based on travel mode:
  1. own_vehicle  → route stops, fuel/CNG/EV stations,
                    food on route, toll, return route
  2. public transport → destination itinerary only
                        (places, hotels, food)
"""

import json
import httpx
from app.core.config import settings
from app.schemas.schemas import TripCreate, ItineraryStop, TripOut, TravelMode


# ── Prompt for Own Vehicle ────────────────────────────────────────────────────

def build_own_vehicle_prompt(trip: TripCreate, vehicle_info: dict) -> str:
    fuel_type = vehicle_info.get("fuel_type", "petrol")
    category  = vehicle_info.get("category", "car")

    fuel_rule = (
        "Add EV charging station stop every 150 km."
        if fuel_type == "electric"
        else "Add petrol/CNG pump stop every 200 km."
    )

    return f"""
You are RoadBuddy AI, India's expert road-trip planner.
Generate a complete road trip itinerary in JSON format.

Trip details:
- Origin: {trip.origin}
- Destination: {trip.destination}
- Dates: {trip.start_date} to {trip.end_date}
- Budget: Rs {trip.budget_inr}
- Vehicle: {fuel_type} {category}
- Group: {trip.group_type} ({trip.num_people} people)

This person is travelling by THEIR OWN VEHICLE.
The itinerary must cover:
  GOING ROUTE  (origin to destination)
  DESTINATION  (places to visit, hotels, food at destination)
  RETURN ROUTE (destination back to origin)

Return ONLY a JSON object in this exact shape, nothing else:
{{
  "total_distance_km": 400,
  "fuel_cost_inr": 2400,
  "toll_cost_inr": 680,
  "return_toll_cost_inr": 680,
  "return_fuel_cost_inr": 2400,
  "hotel_cost_inr": 2500,
  "food_cost_inr": 1200,
  "total_estimated_cost_inr": 9860,
  "ai_summary": "A scenic drive from Jaipur to Udaipur and back...",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "HP Petrol Pump, Ajmer Road",
      "place_type": "fuel",
      "description": "Fill up before leaving Jaipur.",
      "estimated_cost_inr": 2400,
      "lat": null,
      "lng": null
    }}
  ]
}}

Place types allowed:
  going_route    → use for route stops while going
  fuel           → petrol pump / CNG station / EV charging
  food           → dhaba or restaurant on route
  hotel          → overnight stay
  sightseeing    → places to visit at destination
  destination_food → restaurants at destination
  return_route   → stops while returning home

Rules:
- Day 1 morning: start with fuel stop at origin.
- Include morning / afternoon / evening slots each day.
- Add food stop every 150-200 km on route.
- {fuel_rule}
- Add toll reminder stops on highway entry/exit.
- At destination: suggest top places to visit, best hotel, best food.
- Return route: add food stops, fuel stops and toll stops.
- Last stop: reach home safely.
- Stay within Rs {trip.budget_inr} budget.
- For family group add kid friendly stops and clean restrooms.
""".strip()


# ── Prompt for Public Transport ───────────────────────────────────────────────

def build_transport_prompt(trip: TripCreate) -> str:
    return f"""
You are RoadBuddy AI, India's expert trip planner.
Generate a destination itinerary in JSON format.

Trip details:
- Destination: {trip.destination}
- Dates: {trip.start_date} to {trip.end_date}
- Budget: Rs {trip.budget_inr}
- Group: {trip.group_type} ({trip.num_people} people)

This person is travelling by PUBLIC TRANSPORT (bus/train/flight).
They are already at the destination.
The itinerary must cover ONLY:
  - Best places to visit at destination
  - Best hotels to stay
  - Best food and restaurants

Do NOT include any route stops, fuel stops or toll stops.

Return ONLY a JSON object in this exact shape, nothing else:
{{
  "total_distance_km": 0,
  "hotel_cost_inr": 3000,
  "food_cost_inr": 1500,
  "total_estimated_cost_inr": 4500,
  "ai_summary": "Explore the beautiful city of Manali...",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "Hadimba Temple",
      "place_type": "sightseeing",
      "description": "Famous ancient temple surrounded by cedar forest.",
      "estimated_cost_inr": 50,
      "lat": null,
      "lng": null
    }}
  ]
}}

Place types allowed:
  sightseeing      → places to visit
  hotel            → where to stay
  destination_food → restaurants and food places

Rules:
- Include morning / afternoon / evening slots each day.
- Add at least one hotel per day.
- Add at least 2 food stops per day.
- Add at least 2 sightseeing spots per day.
- Stay within Rs {trip.budget_inr} budget.
- For family group add kid friendly places.
""".strip()


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude(prompt: str) -> dict:
    """Call Anthropic Claude API and parse JSON response."""
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )
        res.raise_for_status()
        text = res.json()["content"][0]["text"]
        return json.loads(text)


# ── Mock Data — Own Vehicle ───────────────────────────────────────────────────

def mock_own_vehicle(trip: TripCreate) -> dict:
    return {
        "total_distance_km": 320,
        "fuel_cost_inr": 2400,
        "toll_cost_inr": 680,
        "return_fuel_cost_inr": 2400,
        "return_toll_cost_inr": 680,
        "hotel_cost_inr": 2500,
        "food_cost_inr": 1200,
        "total_estimated_cost_inr": round(trip.budget_inr * 0.85, 2),
        "ai_summary": (
            f"A wonderful road trip from {trip.origin} to "
            f"{trip.destination} and back. Includes scenic route stops, "
            "local dhabas, fuel stops and comfortable stays."
        ),
        "stops": [
            {
                "day": 1, "time_slot": "morning",
                "place_name": f"Petrol Pump — {trip.origin}",
                "place_type": "fuel",
                "description": "Fill up before leaving.",
                "estimated_cost_inr": 2400,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "afternoon",
                "place_name": "Highway Dhaba — Lunch Stop",
                "place_type": "food",
                "description": "Popular dhaba known for dal baati churma.",
                "estimated_cost_inr": 400,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "evening",
                "place_name": f"Hotel Shree Palace — {trip.destination}",
                "place_type": "hotel",
                "description": "Budget hotel. Clean rooms, free parking.",
                "estimated_cost_inr": 1200,
                "lat": None, "lng": None,
            },
            {
                "day": 2, "time_slot": "morning",
                "place_name": "Top Sightseeing Spot",
                "place_type": "sightseeing",
                "description": f"Must visit attraction at {trip.destination}.",
                "estimated_cost_inr": 200,
                "lat": None, "lng": None,
            },
            {
                "day": 2, "time_slot": "afternoon",
                "place_name": "Local Restaurant",
                "place_type": "destination_food",
                "description": "Best local cuisine at destination.",
                "estimated_cost_inr": 500,
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "morning",
                "place_name": f"Petrol Pump — {trip.destination}",
                "place_type": "fuel",
                "description": "Fill up before returning home.",
                "estimated_cost_inr": 2400,
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "afternoon",
                "place_name": "Highway Dhaba — Return Lunch",
                "place_type": "return_route",
                "description": "Food stop on return journey.",
                "estimated_cost_inr": 400,
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "evening",
                "place_name": f"Reach Home — {trip.origin}",
                "place_type": "return_route",
                "description": "Trip complete. Welcome home!",
                "estimated_cost_inr": 0,
                "lat": None, "lng": None,
            },
        ],
    }


# ── Mock Data — Public Transport ──────────────────────────────────────────────

def mock_transport_itinerary(trip: TripCreate) -> dict:
    return {
        "total_distance_km": 0,
        "hotel_cost_inr": 3000,
        "food_cost_inr": 1500,
        "total_estimated_cost_inr": round(trip.budget_inr * 0.75, 2),
        "ai_summary": (
            f"Explore the beautiful {trip.destination}. "
            "Includes top sightseeing spots, best hotels and local food."
        ),
        "stops": [
            {
                "day": 1, "time_slot": "morning",
                "place_name": "Top Attraction",
                "place_type": "sightseeing",
                "description": f"Must visit spot at {trip.destination}.",
                "estimated_cost_inr": 200,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "afternoon",
                "place_name": "Local Restaurant",
                "place_type": "destination_food",
                "description": "Best local cuisine.",
                "estimated_cost_inr": 400,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "evening",
                "place_name": "Hotel Grand",
                "place_type": "hotel",
                "description": "Comfortable stay near city centre.",
                "estimated_cost_inr": 1500,
                "lat": None, "lng": None,
            },
        ],
    }


# ── Main Function ─────────────────────────────────────────────────────────────

async def generate_itinerary(trip: TripCreate, vehicle_info: dict) -> TripOut:
    """
    Main function called from the router.
    Picks the right prompt based on travel_mode.
    """
    try:
        # ── Choose prompt based on travel mode ────────────────────────────────
        if trip.travel_mode == TravelMode.own_vehicle:
            if settings.anthropic_api_key:
                prompt = build_own_vehicle_prompt(trip, vehicle_info)
                data = await call_claude(prompt)
            else:
                data = mock_own_vehicle(trip)
        else:
            # bus / train / flight — destination only
            if settings.anthropic_api_key:
                prompt = build_transport_prompt(trip)
                data = await call_claude(prompt)
            else:
                data = mock_transport_itinerary(trip)

        stops = [ItineraryStop(**s) for s in data["stops"]]

        return TripOut(
            id="trip_" + trip.origin[:3].lower() + trip.destination[:3].lower(),
            origin=trip.origin,
            destination=trip.destination,
            travel_mode=trip.travel_mode,
            total_distance_km=data.get("total_distance_km", 0),
            stops=stops,
            # cost breakdown
            fuel_cost_inr=data.get("fuel_cost_inr", 0),
            toll_cost_inr=data.get("toll_cost_inr", 0) + data.get("return_toll_cost_inr", 0),
            transport_fare_inr=0,   # set by trips.py after booking
            return_fare_inr=0,      # set by trips.py after booking
            hotel_cost_inr=data.get("hotel_cost_inr", 0),
            food_cost_inr=data.get("food_cost_inr", 0),
            total_estimated_cost_inr=data.get("total_estimated_cost_inr", 0),
            ai_summary=data.get("ai_summary", ""),
        )

    except Exception as e:
        raise RuntimeError(f"Itinerary generation failed: {e}")