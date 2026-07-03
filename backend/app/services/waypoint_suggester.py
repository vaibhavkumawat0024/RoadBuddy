"""
AI Waypoint Suggester Service — RoadBuddy (Groq)
"""

import json
import httpx
from app.core.config import settings

GROQ_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_MODEL = "gemini-1.5-flash"


def build_waypoint_prompt(origin, destination, preferences, travel_mode, num_people, group_type):
    pref_text = ", ".join(preferences) if preferences else "general sightseeing"
    group_note = {"family": "Include kid-friendly stops.", "couple": "Include romantic viewpoints.",
                  "friends": "Include adventure and street food spots.", "solo": "Include safe popular stops."}.get(group_type, "")
    mode_note = "Include fuel stops." if travel_mode == "own_vehicle" else "Skip fuel stops."
    return f"""You are RoadBuddy AI, India's expert road trip planner.
Route: {origin} to {destination} | {num_people} people ({group_type}) | Preferences: {pref_text}
{mode_note} {group_note}

Suggest 6-10 real waypoints. Include hidden gems, dhabas, viewpoints, landmarks.
Return ONLY valid JSON, no markdown:
{{
  "route_summary": "One sentence about this route.",
  "total_distance_km": 400,
  "waypoints": [
    {{
      "name": "Place name",
      "type": "nature",
      "distance_from_origin_km": 80,
      "highway": "NH-48",
      "description": "Short description.",
      "why_visit": "Why worth visiting.",
      "best_time": "Morning",
      "estimated_stop_duration_mins": 60,
      "estimated_cost_inr": 0,
      "lat": null,
      "lng": null
    }}
  ]
}}
Types: nature, food, heritage, viewpoint, fuel, adventure, market, hidden_gem"""


from app.services.groq_client import call_groq as call_groq_waypoints


def mock_waypoints(origin, destination):
    return {
        "route_summary": f"The route from {origin} to {destination} passes through scenic highways.",
        "total_distance_km": 350,
        "waypoints": [
            {"name": f"Scenic Viewpoint near {origin}", "type": "viewpoint", "distance_from_origin_km": 50,
             "highway": "NH-48", "description": "Beautiful hilltop viewpoint.", "why_visit": "Great for photos.",
             "best_time": "Early morning", "estimated_stop_duration_mins": 30, "estimated_cost_inr": 0, "lat": None, "lng": None},
            {"name": "Famous Highway Dhaba", "type": "food", "distance_from_origin_km": 120,
             "highway": "NH-48", "description": "Iconic dhaba with Rajasthani thali.", "why_visit": "Best dal baati on this highway.",
             "best_time": "Afternoon", "estimated_stop_duration_mins": 45, "estimated_cost_inr": 300, "lat": None, "lng": None},
            {"name": "Ancient Temple Hidden Gem", "type": "hidden_gem", "distance_from_origin_km": 180,
             "highway": "NH-48", "description": "300-year-old temple off the highway.", "why_visit": "Peaceful and uncrowded.",
             "best_time": "Morning", "estimated_stop_duration_mins": 45, "estimated_cost_inr": 0, "lat": None, "lng": None},
        ],
    }


async def suggest_waypoints(origin, destination, preferences=None, travel_mode="own_vehicle", num_people=2, group_type="friends"):
    try:
        if settings.gemini_api_key:
            data = await call_groq_waypoints(build_waypoint_prompt(origin, destination, preferences or [], travel_mode, num_people, group_type))
        else:
            data = mock_waypoints(origin, destination)
        return {
            "origin": origin, "destination": destination,
            "route_summary": data.get("route_summary", ""),
            "total_distance_km": data.get("total_distance_km", 0),
            "total_waypoints": len(data.get("waypoints", [])),
            "waypoints": data.get("waypoints", []),
        }
    except Exception as e:
        raise RuntimeError(f"Waypoint suggestion failed: {e}")