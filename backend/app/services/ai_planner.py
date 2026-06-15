"""
AI Trip Planner Service — RoadBuddy v2
---------------------------------------
Upgraded with:
  - Real Indian highway (NH) context
  - Proper per-person budget breakdown
  - Season-aware recommendations (summer/winter/monsoon)
  - Group-type specific stops (family/couple/friends/solo)
  - Richer JSON output with highway names and tips
Two modes:
  1. own_vehicle  → full route (going + destination + return)
  2. public transport → destination itinerary only
"""

import json
import httpx
from datetime import date
from app.core.config import settings
from app.schemas.schemas import TripCreate, ItineraryStop, TripOut, TravelMode


# ── Season Detection ──────────────────────────────────────────────────────────

def get_season(start_date) -> str:
    """Detect Indian travel season from trip start date."""
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
        return (
            f"It is SUMMER. Advise travelling early morning (before 9am) to avoid heat. "
            f"Suggest cold drink stops and shaded rest areas. "
            f"Recommend light cotton clothing. Carry extra water."
        )
    elif season == "monsoon":
        return (
            f"It is MONSOON season. Warn about slippery mountain roads near {destination}. "
            f"Suggest checking road status before travel. "
            f"Recommend rain gear and waterproof bags. Avoid flooded routes."
        )
    else:
        return (
            f"It is WINTER. Suggest warm clothing especially for hill stations. "
            f"Warn about fog on highways early morning. "
            f"Recommend starting after 8am when fog clears. "
            f"If going to mountains, check for snow road closures."
        )


# ── Group Tips ────────────────────────────────────────────────────────────────

def get_group_tips(group_type: str, num_people: int) -> str:
    tips = {
        "family": (
            f"This is a FAMILY trip with {num_people} people including children. "
            "Add kid-friendly stops with clean restrooms every 100km. "
            "Suggest family restaurants with kids menu. "
            "Include safe play areas and parks at destination. "
            "Avoid very long drives — max 4 hours driving per day."
        ),
        "couple": (
            f"This is a COUPLE trip. "
            "Suggest romantic viewpoints and sunset spots. "
            "Include candlelight dinner options at destination. "
            "Recommend boutique or heritage hotels over budget stays. "
            "Add photography spots along route."
        ),
        "friends": (
            f"This is a FRIENDS trip with {num_people} people. "
            "Suggest adventure activities — trekking, camping, water sports. "
            "Include local street food spots and night markets. "
            "Add group activity options like bonfires and local tours. "
            "Recommend hostels or group stay options."
        ),
        "solo": (
            "This is a SOLO trip. "
            "Prioritise safety — suggest well-lit rest stops and busy dhabas. "
            "Include solo traveller hostels and guesthouses. "
            "Add local meetup spots and co-working cafes. "
            "Share emergency contact points on route."
        ),
    }
    return tips.get(group_type, f"Group of {num_people} people.")


# ── Budget Breakdown ──────────────────────────────────────────────────────────

def get_budget_breakdown(budget_inr: float, num_people: int,
                          fuel_type: str, travel_mode: str) -> str:
    per_person = budget_inr / max(num_people, 1)

    if travel_mode == "own_vehicle":
        fuel_pct  = 0.30 if fuel_type != "electric" else 0.15
        toll_pct  = 0.10
        hotel_pct = 0.30
        food_pct  = 0.20
        misc_pct  = 0.10
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person)\n"
            f"Suggested split:\n"
            f"  Fuel/Charging : Rs {budget_inr * fuel_pct:.0f}\n"
            f"  Tolls         : Rs {budget_inr * toll_pct:.0f}\n"
            f"  Hotels        : Rs {budget_inr * hotel_pct:.0f}\n"
            f"  Food          : Rs {budget_inr * food_pct:.0f}\n"
            f"  Misc/Entry    : Rs {budget_inr * misc_pct:.0f}\n"
            f"Stay strictly within these limits."
        )
    else:
        hotel_pct = 0.45
        food_pct  = 0.30
        activity_pct = 0.25
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person)\n"
            f"Suggested split:\n"
            f"  Hotels        : Rs {budget_inr * hotel_pct:.0f}\n"
            f"  Food          : Rs {budget_inr * food_pct:.0f}\n"
            f"  Activities    : Rs {budget_inr * activity_pct:.0f}\n"
            f"Stay strictly within these limits."
        )


# ── Prompt for Own Vehicle ────────────────────────────────────────────────────

def build_own_vehicle_prompt(trip: TripCreate, vehicle_info: dict) -> str:
    fuel_type = vehicle_info.get("fuel_type", "petrol")
    category  = vehicle_info.get("category", "car")
    season    = get_season(trip.start_date)

    if fuel_type == "electric":
        fuel_rule = (
            "Add EV charging station stop every 120-150 km. "
            "Mention charging time (30-45 min fast charge). "
            "Only suggest stations from Tata Power, EESL, or ChargeZone networks."
        )
    elif fuel_type == "cng":
        fuel_rule = (
            "Add CNG pump stop every 150 km. "
            "Note that CNG pumps are less common on highways — plan accordingly. "
            "Suggest carrying a petrol backup if CNG unavailable."
        )
    else:
        fuel_rule = (
            "Add petrol pump stop every 200-250 km. "
            "Prefer HP, Indian Oil, or Bharat Petroleum pumps on National Highways."
        )

    season_tips = get_season_tips(season, trip.destination)
    group_tips  = get_group_tips(trip.group_type, trip.num_people)
    budget_info = get_budget_breakdown(
        trip.budget_inr, trip.num_people, fuel_type, "own_vehicle"
    )

    return f"""
You are RoadBuddy AI, India's expert road trip planner with deep knowledge of
Indian National Highways, state highways, dhabas, toll plazas, and travel conditions.

Trip details:
- Origin      : {trip.origin}
- Destination : {trip.destination}
- Dates       : {trip.start_date} to {trip.end_date}
- Vehicle     : {fuel_type} {category}
- Season      : {season.upper()}

{budget_info}

GROUP INSTRUCTIONS:
{group_tips}

SEASON INSTRUCTIONS:
{season_tips}

FUEL INSTRUCTIONS:
{fuel_rule}

This person is travelling by THEIR OWN VEHICLE.
Generate a complete itinerary covering:
  GOING ROUTE  → origin to destination (real towns, NH highways, landmarks)
  DESTINATION  → places to visit, best hotels, best food
  RETURN ROUTE → destination back to origin

IMPORTANT RULES:
- Use REAL Indian town names and National Highway numbers (e.g. NH-48, NH-8)
- Mention actual well-known dhabas or restaurant chains where possible
- Day 1 morning: always start with fuel/charge stop near origin
- Add food stop every 150-200 km on highway
- Add toll reminder at major toll plazas with estimated cost
- At destination: top 3 sightseeing spots, 1 hotel recommendation, 2 food spots
- Return route: at least 2 food stops and 1 fuel stop
- Last stop: safe arrival home message
- All costs must be realistic 2024-2025 Indian prices in INR

Return ONLY a valid JSON object in this exact shape, nothing else:
{{
  "total_distance_km": 400,
  "fuel_cost_inr": 2400,
  "toll_cost_inr": 680,
  "return_toll_cost_inr": 680,
  "return_fuel_cost_inr": 2400,
  "hotel_cost_inr": 2500,
  "food_cost_inr": 1200,
  "total_estimated_cost_inr": 9860,
  "season": "{season}",
  "season_tip": "One key travel tip for this season in 1 sentence.",
  "ai_summary": "A 2-3 sentence engaging summary of this road trip.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "HP Petrol Pump, NH-48, Ajmer Road, Jaipur",
      "place_type": "fuel",
      "description": "Fill up before leaving. NH-48 is the main highway for this route.",
      "estimated_cost_inr": 2400,
      "highway": "NH-48",
      "lat": null,
      "lng": null
    }}
  ]
}}

Place types allowed:
  going_route      → towns or landmarks while going
  fuel             → petrol pump / CNG station / EV charging
  food             → dhaba or restaurant on route
  hotel            → overnight stay
  sightseeing      → places to visit at destination
  destination_food → restaurants at destination
  return_route     → stops while returning home
  toll             → toll plaza reminder

The "highway" field should contain the NH number for route stops, or null for destination stops.
""".strip()


# ── Prompt for Public Transport ───────────────────────────────────────────────

def build_transport_prompt(trip: TripCreate) -> str:
    season      = get_season(trip.start_date)
    season_tips = get_season_tips(season, trip.destination)
    group_tips  = get_group_tips(trip.group_type, trip.num_people)
    budget_info = get_budget_breakdown(
        trip.budget_inr, trip.num_people, "na", "public"
    )

    return f"""
You are RoadBuddy AI, India's expert trip planner with deep knowledge of
Indian tourist destinations, hotels, local food, and travel conditions.

Trip details:
- Destination : {trip.destination}
- Dates       : {trip.start_date} to {trip.end_date}
- Season      : {season.upper()}

{budget_info}

GROUP INSTRUCTIONS:
{group_tips}

SEASON INSTRUCTIONS:
{season_tips}

This person is travelling by PUBLIC TRANSPORT (bus/train/flight).
They will already be AT the destination.
Generate a destination-only itinerary covering:
  - Top places to visit (real, well-known spots)
  - Best hotels (real hotel names with price range)
  - Best food spots (real restaurant or street food names)

DO NOT include route stops, fuel stops, or toll stops.

IMPORTANT RULES:
- Use REAL place names at {trip.destination}
- Suggest actual well-known restaurants or food streets
- Recommend actual hotels with realistic 2024-2025 prices
- Morning: sightseeing. Afternoon: food + rest. Evening: sightseeing or market
- At least 2 sightseeing spots per day
- At least 2 food stops per day
- At least 1 hotel per day
- All costs realistic INR prices

Return ONLY a valid JSON object in this exact shape, nothing else:
{{
  "total_distance_km": 0,
  "hotel_cost_inr": 3000,
  "food_cost_inr": 1500,
  "total_estimated_cost_inr": 4500,
  "season": "{season}",
  "season_tip": "One key travel tip for this season in 1 sentence.",
  "ai_summary": "A 2-3 sentence engaging summary of this trip.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "Hadimba Devi Temple, Manali",
      "place_type": "sightseeing",
      "description": "Ancient 16th century temple surrounded by cedar forest. Entry free. 1-2 hours.",
      "estimated_cost_inr": 50,
      "highway": null,
      "lat": null,
      "lng": null
    }}
  ]
}}

Place types allowed:
  sightseeing      → places to visit
  hotel            → where to stay
  destination_food → restaurants and food places
""".strip()


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude(prompt: str) -> dict:
    """Call Anthropic Claude API and return parsed JSON response."""
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": (
                    prompt
                    + "\n\nIMPORTANT: Return ONLY raw JSON. "
                    "No explanation, no markdown, no code blocks."
                ),
            }
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        res.raise_for_status()
        text = res.json()["content"][0]["text"].strip()

        # Strip markdown code fences if Claude adds them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)


# ── Mock Data — Own Vehicle ───────────────────────────────────────────────────

def mock_own_vehicle(trip: TripCreate) -> dict:
    season = get_season(trip.start_date)
    return {
        "total_distance_km": 320,
        "fuel_cost_inr": 2400,
        "toll_cost_inr": 680,
        "return_fuel_cost_inr": 2400,
        "return_toll_cost_inr": 680,
        "hotel_cost_inr": 2500,
        "food_cost_inr": 1200,
        "total_estimated_cost_inr": round(trip.budget_inr * 0.85, 2),
        "season": season,
        "season_tip": "Check road conditions before leaving.",
        "ai_summary": (
            f"A wonderful road trip from {trip.origin} to "
            f"{trip.destination} and back. Includes scenic route stops, "
            "local dhabas, fuel stops, and comfortable stays."
        ),
        "stops": [
            {
                "day": 1, "time_slot": "morning",
                "place_name": f"HP Petrol Pump, NH-48, {trip.origin}",
                "place_type": "fuel",
                "description": "Fill up before leaving. Keep tank full for the highway.",
                "estimated_cost_inr": 2400,
                "highway": "NH-48",
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "afternoon",
                "place_name": "Apna Dhaba — Highway Lunch Stop",
                "place_type": "food",
                "description": "Popular highway dhaba known for dal baati churma and lassi.",
                "estimated_cost_inr": 400,
                "highway": "NH-48",
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "evening",
                "place_name": f"Hotel Shree Palace, {trip.destination}",
                "place_type": "hotel",
                "description": "Budget-friendly hotel. Clean rooms, free parking, 24hr reception.",
                "estimated_cost_inr": 1200,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 2, "time_slot": "morning",
                "place_name": f"Main Attraction, {trip.destination}",
                "place_type": "sightseeing",
                "description": f"Top must-visit attraction at {trip.destination}. Entry ~Rs 100.",
                "estimated_cost_inr": 200,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 2, "time_slot": "afternoon",
                "place_name": "Local Thali Restaurant",
                "place_type": "destination_food",
                "description": "Authentic local cuisine. Try the regional thali for Rs 150-200.",
                "estimated_cost_inr": 500,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "morning",
                "place_name": f"Indian Oil Pump, {trip.destination}",
                "place_type": "fuel",
                "description": "Fill up before heading back home.",
                "estimated_cost_inr": 2400,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "afternoon",
                "place_name": "Highway Dhaba — Return Lunch",
                "place_type": "return_route",
                "description": "Good pit stop on the return journey. Try local snacks.",
                "estimated_cost_inr": 400,
                "highway": "NH-48",
                "lat": None, "lng": None,
            },
            {
                "day": 3, "time_slot": "evening",
                "place_name": f"Home — {trip.origin}",
                "place_type": "return_route",
                "description": "Trip complete! Welcome home. Total distance covered: ~320 km each way.",
                "estimated_cost_inr": 0,
                "highway": None,
                "lat": None, "lng": None,
            },
        ],
    }


# ── Mock Data — Public Transport ──────────────────────────────────────────────

def mock_transport_itinerary(trip: TripCreate) -> dict:
    season = get_season(trip.start_date)
    return {
        "total_distance_km": 0,
        "hotel_cost_inr": 3000,
        "food_cost_inr": 1500,
        "total_estimated_cost_inr": round(trip.budget_inr * 0.75, 2),
        "season": season,
        "season_tip": "Carry appropriate clothing for the season.",
        "ai_summary": (
            f"Explore the beautiful {trip.destination}. "
            "Includes top sightseeing spots, best local food, and comfortable stays."
        ),
        "stops": [
            {
                "day": 1, "time_slot": "morning",
                "place_name": f"Top Attraction, {trip.destination}",
                "place_type": "sightseeing",
                "description": f"Must-visit iconic spot at {trip.destination}. Entry ~Rs 100.",
                "estimated_cost_inr": 200,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "afternoon",
                "place_name": "Local Food Street",
                "place_type": "destination_food",
                "description": "Try the best local street food and regional specialties.",
                "estimated_cost_inr": 400,
                "highway": None,
                "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "evening",
                "place_name": "Hotel Grand Inn",
                "place_type": "hotel",
                "description": "Comfortable stay near city centre. Clean rooms, good reviews.",
                "estimated_cost_inr": 1500,
                "highway": None,
                "lat": None, "lng": None,
            },
        ],
    }


# ── Main Function ─────────────────────────────────────────────────────────────

async def generate_itinerary(trip: TripCreate, vehicle_info: dict) -> TripOut:
    """
    Main entry point called from the router.
    Selects prompt based on travel_mode and calls Claude API.
    Falls back to mock data if API key is missing.
    """
    try:
        if trip.travel_mode == TravelMode.own_vehicle:
            if settings.anthropic_api_key:
                prompt = build_own_vehicle_prompt(trip, vehicle_info)
                data   = await call_claude(prompt)
            else:
                data = mock_own_vehicle(trip)
        else:
            if settings.anthropic_api_key:
                prompt = build_transport_prompt(trip)
                data   = await call_claude(prompt)
            else:
                data = mock_transport_itinerary(trip)

        stops = [ItineraryStop(**s) for s in data["stops"]]

        return TripOut(
            id=f"trip_{trip.origin[:3].lower()}{trip.destination[:3].lower()}",
            origin=trip.origin,
            destination=trip.destination,
            travel_mode=trip.travel_mode,
            total_distance_km=data.get("total_distance_km", 0),
            stops=stops,
            fuel_cost_inr=data.get("fuel_cost_inr", 0),
            toll_cost_inr=(
                data.get("toll_cost_inr", 0)
                + data.get("return_toll_cost_inr", 0)
            ),
            transport_fare_inr=0,
            return_fare_inr=0,
            hotel_cost_inr=data.get("hotel_cost_inr", 0),
            food_cost_inr=data.get("food_cost_inr", 0),
            total_estimated_cost_inr=data.get("total_estimated_cost_inr", 0),
            ai_summary=data.get("ai_summary", ""),
        )

    except Exception as e:
        raise RuntimeError(f"Itinerary generation failed: {e}")