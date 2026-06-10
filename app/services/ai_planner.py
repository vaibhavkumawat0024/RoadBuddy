"""
AI Trip Planner Service
-----------------------
Builds a prompt from trip details and calls the LLM (Claude or GPT)
to generate a JSON itinerary.  The response is then enriched with
real place data (placeholder here — swap in Google Places API calls).
"""

import json
import httpx
from app.core.config import settings
from app.schemas.schemas import TripCreate, ItineraryStop, TripOut


def build_prompt(trip: TripCreate, vehicle_info: dict) -> str:
    return f"""
You are RoadBuddy AI, India's expert road-trip planner.
Generate a day-by-day road trip itinerary in JSON format.

Trip details:
- Origin: {trip.origin}
- Destination: {trip.destination}
- Dates: {trip.start_date} to {trip.end_date}
- Total budget: ₹{trip.budget_inr}
- Vehicle: {vehicle_info.get('fuel_type','petrol')} {vehicle_info.get('category','car')}
- Group: {trip.group_type} ({trip.num_people} people)

Return ONLY a JSON object in this exact shape, nothing else:
{{
  "total_distance_km": 250,
  "total_estimated_cost_inr": 8000,
  "ai_summary": "A scenic 3-day drive from Jaipur to Udaipur...",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "Ajmer Dargah",
      "place_type": "sightseeing",
      "description": "Brief visit to the famous shrine.",
      "estimated_cost_inr": 200,
      "lat": 26.4499,
      "lng": 74.6399
    }}
  ]
}}

Rules:
- Include morning / afternoon / evening slots each day.
- Add at least one dhaba or restaurant stop per day.
- Add at least one fuel stop per 200 km.
- If the vehicle is electric, add charging stop instead of fuel.
- Stay within the ₹{trip.budget_inr} budget.
- For family group, add kid-friendly stops and clean restroom locations.
""".strip()


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
        res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        res.raise_for_status()
        text = res.json()["content"][0]["text"]
        return json.loads(text)


def mock_itinerary(trip: TripCreate) -> dict:
    """
    Returns a mock itinerary so you can test the API
    without burning LLM API credits during development.
    """
    return {
        "total_distance_km": 320,
        "total_estimated_cost_inr": trip.budget_inr * 0.85,
        "ai_summary": f"A wonderful road trip from {trip.origin} to {trip.destination}. "
                      "Includes scenic viewpoints, local dhabas, and comfortable stays.",
        "stops": [
            {
                "day": 1, "time_slot": "morning",
                "place_name": "Starting point — fuel up",
                "place_type": "fuel",
                "description": "Fill the tank before you leave.",
                "estimated_cost_inr": 2500, "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "afternoon",
                "place_name": "Roadside Dhaba — Lunch",
                "place_type": "food",
                "description": "Famous highway dhaba known for dal baati.",
                "estimated_cost_inr": 400, "lat": None, "lng": None,
            },
            {
                "day": 1, "time_slot": "evening",
                "place_name": "Hotel Shree Palace",
                "place_type": "hotel",
                "description": "Budget hotel near city centre. Clean rooms, parking available.",
                "estimated_cost_inr": 1200, "lat": None, "lng": None,
            },
        ],
    }


async def generate_itinerary(trip: TripCreate, vehicle_info: dict) -> TripOut:
    """Main function — call this from the router."""
    try:
        if settings.anthropic_api_key:
            prompt = build_prompt(trip, vehicle_info)
            data = await call_claude(prompt)
        else:
            # Fall back to mock data during local development
            data = mock_itinerary(trip)

        stops = [ItineraryStop(**s) for s in data["stops"]]

        return TripOut(
            id="trip_" + trip.origin[:3].lower() + trip.destination[:3].lower(),
            origin=trip.origin,
            destination=trip.destination,
            total_distance_km=data["total_distance_km"],
            stops=stops,
            total_estimated_cost_inr=data["total_estimated_cost_inr"],
            ai_summary=data["ai_summary"],
        )
    except Exception as e:
        raise RuntimeError(f"Itinerary generation failed: {e}")
