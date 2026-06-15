"""
AI Route Safety Analyzer Service — RoadBuddy (Groq)
"""

import json
import httpx
from app.core.config import settings
from datetime import date

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def get_season(travel_date: str) -> str:
    try:
        month = int(travel_date.split("-")[1])
    except Exception:
        month = date.today().month
    if month in [3, 4, 5]: return "summer"
    elif month in [6, 7, 8, 9]: return "monsoon"
    else: return "winter"


def build_safety_prompt(origin, destination, travel_date, departure_time, vehicle_type, num_people):
    season = get_season(travel_date)
    return f"""You are RoadBuddy AI, India's expert road safety analyst.
Route: {origin} to {destination} | Date: {travel_date} | Season: {season.upper()}
Departure: {departure_time} | Vehicle: {vehicle_type} | People: {num_people}

Analyze this route for safety. Return ONLY valid JSON, no markdown:
{{
  "route": "{origin} to {destination}",
  "travel_date": "{travel_date}",
  "season": "{season}",
  "overall_safety_score": 8,
  "overall_safety_level": "safe",
  "summary": "2-3 sentence safety assessment.",
  "departure_advice": "Advice based on {departure_time} departure.",
  "hazards": [
    {{
      "name": "Hazard name",
      "type": "mountain_road",
      "severity": "high",
      "location": "Approximate location",
      "highway": "NH-48",
      "description": "What makes this dangerous.",
      "advice": "How to handle safely."
    }}
  ],
  "safe_stretches": [{{"name": "Safe stretch", "highway": "NH-48", "description": "Why safe."}}],
  "emergency_contacts": [
    {{"name": "Highway Police", "number": "1033", "type": "police"}},
    {{"name": "Ambulance", "number": "108", "type": "medical"}},
    {{"name": "Road Accident Emergency", "number": "1073", "type": "accident"}},
    {{"name": "Tourist Helpline", "number": "1800-11-1363", "type": "tourist"}}
  ],
  "safety_tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4"],
  "best_departure_time": "Recommended time",
  "estimated_safe_driving_hours": 6,
  "recommended_breaks": [{{"location": "Town", "km_from_origin": 150, "reason": "Why stop."}}]
}}
Hazard types: mountain_road, ghat_section, flood_prone, landslide_zone, fog_zone, wildlife_zone, accident_prone, night_risk
Severity: low, medium, high, critical"""


async def call_groq_safety(prompt: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.5, "max_tokens": 3000}
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())


def mock_safety_report(origin, destination, travel_date, departure_time):
    season = get_season(travel_date)
    return {
        "route": f"{origin} to {destination}", "travel_date": travel_date, "season": season,
        "overall_safety_score": 7, "overall_safety_level": "safe",
        "summary": f"The route from {origin} to {destination} is generally safe. Be aware of {season} hazards.",
        "departure_advice": f"Departing at {departure_time} is reasonable. Check tyres and fuel before starting.",
        "hazards": [
            {"name": "Night driving risk", "type": "night_risk", "severity": "medium",
             "location": "All highway sections", "highway": "NH-48",
             "description": "Stray animals and poor visibility after dark.", "advice": "Avoid driving after 9pm."}
        ],
        "safe_stretches": [{"name": f"Main highway near {origin}", "highway": "NH-48", "description": "Well-maintained 4-lane highway."}],
        "emergency_contacts": [
            {"name": "Highway Police", "number": "1033", "type": "police"},
            {"name": "Ambulance", "number": "108", "type": "medical"},
            {"name": "Road Accident Emergency", "number": "1073", "type": "accident"},
            {"name": "Tourist Helpline", "number": "1800-11-1363", "type": "tourist"},
        ],
        "safety_tips": ["Always wear seatbelts", "No mobile phone while driving", "Break every 2 hours", "Carry emergency kit"],
        "best_departure_time": "6:00 AM", "estimated_safe_driving_hours": 7,
        "recommended_breaks": [{"location": f"Midpoint between {origin} and {destination}", "km_from_origin": 150, "reason": "Fuel, food, rest."}],
    }


async def analyze_route_safety(origin, destination, travel_date, departure_time="08:00", vehicle_type="car", num_people=2):
    try:
        if settings.groq_api_key:
            data = await call_groq_safety(build_safety_prompt(origin, destination, travel_date, departure_time, vehicle_type, num_people))
        else:
            data = mock_safety_report(origin, destination, travel_date, departure_time)
        return {"origin": origin, "destination": destination, "safety_report": data}
    except Exception as e:
        raise RuntimeError(f"Safety analysis failed: {e}")