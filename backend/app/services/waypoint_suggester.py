"""
AI Waypoint Suggester Service — RoadBuddy
------------------------------------------
Suggests hidden gems, dhabas, viewpoints, fuel stops,
and "people also visit" style waypoints between
origin and destination using Claude AI.
"""

import json
import httpx
from app.core.config import settings


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_waypoint_prompt(
    origin: str,
    destination: str,
    preferences: list[str],
    travel_mode: str,
    num_people: int,
    group_type: str,
) -> str:

    pref_text = ", ".join(preferences) if preferences else "general sightseeing"

    group_note = {
        "family":  "Include kid-friendly stops with clean restrooms.",
        "couple":  "Include romantic viewpoints and scenic spots.",
        "friends": "Include adventure spots, street food, and offbeat places.",
        "solo":    "Include safe, well-known stops popular with solo travellers.",
    }.get(group_type, "")

    mode_note = (
        "This person is driving their own vehicle so include fuel stops and toll info."
        if travel_mode == "own_vehicle"
        else "This person is travelling by public transport — skip fuel stops."
    )

    return f"""
You are RoadBuddy AI, India's expert road trip planner with deep knowledge of
Indian highways, hidden gems, local dhabas, viewpoints, and tourist spots.

Route details:
- From         : {origin}
- To           : {destination}
- Travellers   : {num_people} people ({group_type})
- Preferences  : {pref_text}

{mode_note}
{group_note}

Suggest the BEST waypoints a traveller should stop at between {origin} and {destination}.
Include a mix of:
  - Hidden gems most tourists miss
  - Famous viewpoints and photo spots
  - Popular local dhabas and food stops
  - Historical or cultural landmarks
  - Nature spots (waterfalls, lakes, forests)
  - "People also visit" type stops nearby the route

RULES:
- Use REAL place names that actually exist on or near this route
- Include distance from origin for each stop (approximate km)
- Mention which National Highway the stop is near
- Give a short "why visit" reason for each stop
- Suggest best time of day to visit each stop
- All stops must be genuinely ON or very close to the route
- Return between 6 to 10 waypoints

Return ONLY a valid JSON object in this exact shape, nothing else:
{{
  "route_summary": "One sentence describing the overall route character.",
  "total_distance_km": 400,
  "waypoints": [
    {{
      "name": "Sambhar Salt Lake",
      "type": "nature",
      "distance_from_origin_km": 80,
      "highway": "NH-48",
      "description": "Asia's largest inland saltwater lake. Famous for flamingos in winter.",
      "why_visit": "Stunning photography spot, rare flamingo sighting in winter months.",
      "best_time": "Early morning",
      "estimated_stop_duration_mins": 60,
      "estimated_cost_inr": 0,
      "lat": null,
      "lng": null
    }}
  ]
}}

Waypoint types allowed:
  nature       → lakes, waterfalls, forests, mountains
  food         → dhabas, restaurants, street food
  heritage     → forts, temples, historical sites
  viewpoint    → scenic spots, photo points
  fuel         → petrol pumps, EV charging (only for own_vehicle)
  adventure    → trekking, water sports, camping
  market       → local bazaars, shopping streets
  hidden_gem   → offbeat places most tourists miss
""".strip()


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude_waypoints(prompt: str) -> dict:
    """Call Claude API and return parsed waypoint JSON."""
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 3000,
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

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        return json.loads(text)


# ── Mock Data ─────────────────────────────────────────────────────────────────

def mock_waypoints(origin: str, destination: str) -> dict:
    return {
        "route_summary": (
            f"The route from {origin} to {destination} passes through "
            "scenic highways with multiple interesting stops."
        ),
        "total_distance_km": 350,
        "waypoints": [
            {
                "name": f"Scenic Viewpoint — near {origin}",
                "type": "viewpoint",
                "distance_from_origin_km": 50,
                "highway": "NH-48",
                "description": "Beautiful hilltop viewpoint with panoramic views.",
                "why_visit": "Best sunrise spot on this route. Great for photos.",
                "best_time": "Early morning",
                "estimated_stop_duration_mins": 30,
                "estimated_cost_inr": 0,
                "lat": None,
                "lng": None,
            },
            {
                "name": "Famous Highway Dhaba",
                "type": "food",
                "distance_from_origin_km": 120,
                "highway": "NH-48",
                "description": "Iconic dhaba serving authentic Rajasthani thali since 1985.",
                "why_visit": "Best dal baati churma on this highway. Locals love it.",
                "best_time": "Afternoon",
                "estimated_stop_duration_mins": 45,
                "estimated_cost_inr": 300,
                "lat": None,
                "lng": None,
            },
            {
                "name": "Ancient Temple — Hidden Gem",
                "type": "hidden_gem",
                "distance_from_origin_km": 180,
                "highway": "NH-48",
                "description": "300-year-old temple hidden 5km off the highway. Rarely visited.",
                "why_visit": "Peaceful, uncrowded, stunning architecture. Most tourists skip it.",
                "best_time": "Morning or evening",
                "estimated_stop_duration_mins": 45,
                "estimated_cost_inr": 0,
                "lat": None,
                "lng": None,
            },
            {
                "name": "Local Market & Bazaar",
                "type": "market",
                "distance_from_origin_km": 230,
                "highway": "NH-48",
                "description": "Vibrant local market with handicrafts, spices, and street food.",
                "why_visit": "Pick up local souvenirs and try street snacks.",
                "best_time": "Afternoon",
                "estimated_stop_duration_mins": 60,
                "estimated_cost_inr": 500,
                "lat": None,
                "lng": None,
            },
            {
                "name": f"Scenic Lake — near {destination}",
                "type": "nature",
                "distance_from_origin_km": 300,
                "highway": "NH-48",
                "description": "Beautiful lake with boating and picnic spots.",
                "why_visit": "Perfect last stop before reaching destination. Relax and refresh.",
                "best_time": "Evening",
                "estimated_stop_duration_mins": 60,
                "estimated_cost_inr": 100,
                "lat": None,
                "lng": None,
            },
        ],
    }


# ── Main Function ─────────────────────────────────────────────────────────────

async def suggest_waypoints(
    origin: str,
    destination: str,
    preferences: list[str] = None,
    travel_mode: str = "own_vehicle",
    num_people: int = 2,
    group_type: str = "friends",
) -> dict:
    """
    Main function called from the router.
    Returns AI-suggested waypoints between origin and destination.
    """
    try:
        if settings.anthropic_api_key:
            prompt = build_waypoint_prompt(
                origin=origin,
                destination=destination,
                preferences=preferences or [],
                travel_mode=travel_mode,
                num_people=num_people,
                group_type=group_type,
            )
            data = await call_claude_waypoints(prompt)
        else:
            data = mock_waypoints(origin, destination)

        return {
            "origin": origin,
            "destination": destination,
            "route_summary": data.get("route_summary", ""),
            "total_distance_km": data.get("total_distance_km", 0),
            "total_waypoints": len(data.get("waypoints", [])),
            "waypoints": data.get("waypoints", []),
        }

    except Exception as e:
        raise RuntimeError(f"Waypoint suggestion failed: {e}")