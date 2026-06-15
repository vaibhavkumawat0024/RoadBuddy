"""
AI Route Safety Analyzer Service — RoadBuddy
---------------------------------------------
Analyzes a road trip route and flags:
  - Risky road stretches (mountain, ghat, desert)
  - Flood-prone and landslide-prone areas
  - Night driving warnings
  - Seasonal hazards
  - Safety score out of 10
  - Emergency contact points on route
"""

import httpx
from app.core.config import settings
from datetime import date


# ── Season Detection ──────────────────────────────────────────────────────────

def get_season(travel_date: str) -> str:
    try:
        month = int(travel_date.split("-")[1])
    except Exception:
        month = date.today().month
    if month in [3, 4, 5]:
        return "summer"
    elif month in [6, 7, 8, 9]:
        return "monsoon"
    else:
        return "winter"


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_safety_prompt(
    origin: str,
    destination: str,
    travel_date: str,
    departure_time: str,
    vehicle_type: str,
    num_people: int,
) -> str:
    season = get_season(travel_date)

    return f"""
You are RoadBuddy AI, India's expert road safety analyst with deep knowledge of
Indian highways, dangerous road stretches, seasonal hazards, and emergency services.

Route details:
- From           : {origin}
- To             : {destination}
- Travel date    : {travel_date}
- Departure time : {departure_time}
- Season         : {season.upper()}
- Vehicle        : {vehicle_type}
- Travellers     : {num_people} people

Analyze this route for safety and return a comprehensive safety report.

Consider:
  - Known dangerous stretches on this route (sharp curves, blind spots, narrow roads)
  - Ghat sections, mountain passes, or hilly terrain
  - Flood-prone areas during monsoon
  - Landslide-prone zones
  - Night driving risks on this specific route
  - Seasonal hazards for {season}
  - Highway quality and road condition reputation
  - Wildlife crossing zones
  - Fog-prone stretches in winter
  - Accident-prone black spots on Indian highways

Return ONLY a valid JSON object in this exact shape, nothing else:
{{
  "route": "{origin} to {destination}",
  "travel_date": "{travel_date}",
  "season": "{season}",
  "overall_safety_score": 8,
  "overall_safety_level": "safe",
  "summary": "2-3 sentence overall safety assessment of this route.",
  "departure_advice": "Specific advice based on the {departure_time} departure time.",
  "hazards": [
    {{
      "name": "Name of the hazard or dangerous stretch",
      "type": "mountain_road",
      "severity": "high",
      "location": "Approximate location or km marker",
      "highway": "NH-48",
      "description": "What makes this stretch dangerous.",
      "advice": "Specific advice to handle this hazard safely."
    }}
  ],
  "safe_stretches": [
    {{
      "name": "Name of a safe, good quality stretch",
      "highway": "NH-48",
      "description": "Why this stretch is safe and comfortable."
    }}
  ],
  "emergency_contacts": [
    {{
      "name": "Highway Police Helpline",
      "number": "1033",
      "type": "police"
    }},
    {{
      "name": "Ambulance",
      "number": "108",
      "type": "medical"
    }},
    {{
      "name": "Road Accident Emergency",
      "number": "1073",
      "type": "accident"
    }}
  ],
  "safety_tips": [
    "Specific safety tip for this route and season",
    "Another important tip",
    "One more critical tip",
    "Final tip"
  ],
  "best_departure_time": "Recommended departure time for this route",
  "estimated_safe_driving_hours": 6,
  "recommended_breaks": [
    {{
      "location": "Town or landmark name",
      "km_from_origin": 150,
      "reason": "Why to stop here"
    }}
  ]
}}

Hazard types allowed:
  mountain_road    → steep or winding mountain roads
  ghat_section     → ghat roads with sharp turns
  flood_prone      → areas that flood during monsoon
  landslide_zone   → landslide-prone areas
  fog_zone         → winter fog-prone highway stretches
  wildlife_zone    → areas with animal crossings
  accident_prone   → known black spots with high accident rates
  night_risk       → stretches unsafe for night driving
  construction     → ongoing road construction zones

Severity levels: low, medium, high, critical

Safety score guide:
  9-10 → very safe route
  7-8  → safe with minor cautions
  5-6  → moderate risk, extra care needed
  3-4  → high risk, avoid if possible
  1-2  → very dangerous, reconsider travel
""".strip()


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude_safety(prompt: str) -> dict:
    """Call Claude API and return parsed safety report JSON."""
    import json
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
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())


# ── Mock Safety Report ────────────────────────────────────────────────────────

def mock_safety_report(
    origin: str,
    destination: str,
    travel_date: str,
    departure_time: str,
) -> dict:
    season = get_season(travel_date)

    season_hazard = {
        "summer": {
            "name": "Heat exhaustion risk on highway",
            "type": "night_risk",
            "severity": "medium",
            "description": "Extreme heat between 12pm-4pm. Risk of tyre blowouts and driver fatigue.",
            "advice": "Avoid driving between 12pm-4pm. Keep water, rest in shade."
        },
        "monsoon": {
            "name": "Waterlogging and flash floods",
            "type": "flood_prone",
            "severity": "high",
            "description": "Low-lying highway sections flood during heavy rain. Visibility drops sharply.",
            "advice": "Check weather forecast. Never drive through flooded roads. Wait it out."
        },
        "winter": {
            "name": "Dense fog on highway",
            "type": "fog_zone",
            "severity": "high",
            "description": "Severe fog between 5am-9am reduces visibility to near zero.",
            "advice": "Use fog lights. Drive at 40kmph max in fog. Never use high beam."
        },
    }.get(season, {})

    return {
        "route": f"{origin} to {destination}",
        "travel_date": travel_date,
        "season": season,
        "overall_safety_score": 7,
        "overall_safety_level": "safe",
        "summary": (
            f"The route from {origin} to {destination} is generally safe for travel. "
            f"During {season}, there are some specific hazards to be aware of. "
            f"Follow the safety tips and drive carefully on highway stretches."
        ),
        "departure_advice": (
            f"Departing at {departure_time} is reasonable. "
            "Ensure your vehicle is serviced, tyres are properly inflated, "
            "and you have enough fuel before starting."
        ),
        "hazards": [
            {
                "name": season_hazard.get("name", "General highway risk"),
                "type": season_hazard.get("type", "accident_prone"),
                "severity": season_hazard.get("severity", "medium"),
                "location": f"Various stretches between {origin} and {destination}",
                "highway": "NH-48",
                "description": season_hazard.get("description", "Stay alert on highway."),
                "advice": season_hazard.get("advice", "Drive carefully and take breaks."),
            },
            {
                "name": "Night driving risk",
                "type": "night_risk",
                "severity": "medium",
                "location": "All highway sections",
                "highway": "NH-48",
                "description": "Stray animals, unlit vehicles, and poor visibility after dark.",
                "advice": "Avoid driving after 9pm. If unavoidable, drive at 60kmph max.",
            },
        ],
        "safe_stretches": [
            {
                "name": f"Main highway section near {origin}",
                "highway": "NH-48",
                "description": "Well-maintained 4-lane highway with good lighting and signage.",
            }
        ],
        "emergency_contacts": [
            {"name": "Highway Police Helpline", "number": "1033", "type": "police"},
            {"name": "Ambulance", "number": "108", "type": "medical"},
            {"name": "Road Accident Emergency", "number": "1073", "type": "accident"},
            {"name": "Tourist Helpline", "number": "1800-11-1363", "type": "tourist"},
        ],
        "safety_tips": [
            "Always wear seatbelts — front and back seats",
            "Do not use mobile phone while driving",
            f"Take a break every 2 hours — fatigue is the biggest highway killer",
            "Keep emergency kit: torch, first aid, water, jump cables",
        ],
        "best_departure_time": "6:00 AM — avoid peak heat and reach before dark",
        "estimated_safe_driving_hours": 7,
        "recommended_breaks": [
            {
                "location": f"Midpoint town between {origin} and {destination}",
                "km_from_origin": 150,
                "reason": "Fuel, food, and rest. Good facilities available.",
            }
        ],
    }


# ── Main Function ─────────────────────────────────────────────────────────────

async def analyze_route_safety(
    origin: str,
    destination: str,
    travel_date: str,
    departure_time: str = "08:00",
    vehicle_type: str = "car",
    num_people: int = 2,
) -> dict:
    """
    Main function called from the router.
    Returns a comprehensive safety report for the route.
    """
    try:
        if settings.anthropic_api_key:
            prompt = build_safety_prompt(
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                departure_time=departure_time,
                vehicle_type=vehicle_type,
                num_people=num_people,
            )
            data = await call_claude_safety(prompt)
        else:
            data = mock_safety_report(
                origin=origin,
                destination=destination,
                travel_date=travel_date,
                departure_time=departure_time,
            )

        return {
            "origin": origin,
            "destination": destination,
            "safety_report": data,
        }

    except Exception as e:
        raise RuntimeError(f"Safety analysis failed: {e}")