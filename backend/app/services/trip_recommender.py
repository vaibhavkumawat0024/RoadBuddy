"""
AI Trip Recommender Service — RoadBuddy
-----------------------------------------
Suggests personalized trip ideas based on:
  - User's home city
  - Budget
  - Group type (family, couple, friends, solo)
  - Season / travel dates
  - Interests (adventure, heritage, nature, food, beach)
  - Trip duration
"""

import json
import httpx
from app.core.config import settings

GROQ_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_MODEL = "gemini-1.5-flash"


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_recommender_prompt(
    home_city: str,
    budget_inr: float,
    group_type: str,
    num_people: int,
    duration_days: int,
    season: str,
    interests: list[str],
) -> str:
    interests_text = ", ".join(interests) if interests else "general sightseeing"

    return f"""You are RoadBuddy AI, India's expert travel recommender.

User details:
- Home city    : {home_city}
- Budget       : Rs {budget_inr:.0f} total
- Group        : {group_type} ({num_people} people)
- Duration     : {duration_days} days
- Season       : {season}
- Interests    : {interests_text}

Suggest 5 personalized road trip ideas from {home_city}.
Each trip should be reachable by road from {home_city}.
Match the budget, group type, season, and interests.

Return ONLY valid JSON, no markdown:
{{
  "home_city": "{home_city}",
  "total_recommendations": 5,
  "recommendations": [
    {{
      "rank": 1,
      "title": "Catchy trip title",
      "destination": "Destination city/place",
      "distance_km": 300,
      "highway": "NH-48",
      "duration_days": {duration_days},
      "estimated_cost_inr": 8000,
      "cost_per_person_inr": 4000,
      "destination_type": "hill_station",
      "best_for": "Why this is perfect for this group type",
      "highlights": ["Top attraction 1", "Top attraction 2", "Top attraction 3"],
      "best_season": "{season}",
      "why_recommended": "Personalized reason why this matches their preferences.",
      "difficulty_level": "easy",
      "must_try_food": "Local dish to try at this destination"
    }}
  ],
  "recommendation_tip": "One overall travel tip for this user based on their preferences."
}}

Rules:
- All destinations must be reachable by road from {home_city}
- Rank by best match to user preferences
- difficulty_level: easy, moderate, or challenging
- destination_type: beach, hill_station, heritage, desert, forest, city, religious, adventure
- Vary the destination types across 5 recommendations
- All costs realistic 2024-2025 INR prices
- estimated_cost_inr must be within Rs {budget_inr:.0f} budget
- For {season}: suggest season-appropriate destinations
- For {group_type}: suggest group-appropriate activities
- Use REAL Indian place names and actual NH highway numbers
"""


# ── Call Groq API ─────────────────────────────────────────────────────────────

from app.services.groq_client import call_groq as call_groq_recommender


# ── Mock Recommendations ──────────────────────────────────────────────────────

def mock_recommendations(
    home_city: str,
    budget_inr: float,
    group_type: str,
    num_people: int,
    duration_days: int,
    season: str,
    interests: list[str],
) -> dict:
    per_person = budget_inr / max(num_people, 1)

    destinations = {
        "Jaipur": [
            {"destination": "Udaipur", "distance_km": 393, "highway": "NH-48", "type": "heritage",
             "title": "Lake City Romance — Jaipur to Udaipur", "cost": min(budget_inr * 0.7, 12000),
             "highlights": ["City Palace", "Lake Pichola", "Jagdish Temple"], "food": "Dal Baati Churma"},
            {"destination": "Pushkar", "distance_km": 145, "highway": "NH-58", "type": "religious",
             "title": "Holy Dunes — Jaipur to Pushkar", "cost": min(budget_inr * 0.4, 6000),
             "highlights": ["Pushkar Lake", "Brahma Temple", "Camel Fair Ground"], "food": "Malpua"},
            {"destination": "Ranthambore", "distance_km": 180, "highway": "NH-52", "type": "forest",
             "title": "Tiger Trail — Jaipur to Ranthambore", "cost": min(budget_inr * 0.6, 10000),
             "highlights": ["Tiger Safari", "Ranthambore Fort", "Padam Lake"], "food": "Laal Maas"},
            {"destination": "Mount Abu", "distance_km": 490, "highway": "NH-48", "type": "hill_station",
             "title": "Rajasthan's Hill Escape — Jaipur to Mount Abu", "cost": min(budget_inr * 0.8, 14000),
             "highlights": ["Dilwara Temples", "Nakki Lake", "Guru Shikhar"], "food": "Ker Sangri"},
            {"destination": "Mandawa", "distance_km": 180, "highway": "NH-11", "type": "heritage",
             "title": "Painted Havelis — Jaipur to Mandawa", "cost": min(budget_inr * 0.5, 8000),
             "highlights": ["Mandawa Haveli", "Shekhawati Frescoes", "Mandawa Fort"], "food": "Bajre ki Roti"},
        ]
    }

    default_destinations = [
        {"destination": "Nearest Hill Station", "distance_km": 200, "highway": "NH-1", "type": "hill_station",
         "title": f"Weekend Escape from {home_city}", "cost": min(budget_inr * 0.6, 10000),
         "highlights": ["Scenic Views", "Local Market", "Nature Walks"], "food": "Local Cuisine"},
        {"destination": "Nearest Heritage City", "distance_km": 300, "highway": "NH-2", "type": "heritage",
         "title": f"Heritage Trail from {home_city}", "cost": min(budget_inr * 0.7, 12000),
         "highlights": ["Historic Fort", "Palace", "Local Bazaar"], "food": "Regional Thali"},
        {"destination": "Nearest Nature Spot", "distance_km": 150, "highway": "NH-3", "type": "forest",
         "title": f"Nature Getaway from {home_city}", "cost": min(budget_inr * 0.5, 8000),
         "highlights": ["Wildlife", "Trekking", "Waterfalls"], "food": "Forest Cuisine"},
        {"destination": "Nearest Religious Site", "distance_km": 100, "highway": "NH-4", "type": "religious",
         "title": f"Spiritual Journey from {home_city}", "cost": min(budget_inr * 0.4, 6000),
         "highlights": ["Ancient Temple", "Sacred Lake", "Ashram"], "food": "Prasad Thali"},
        {"destination": "Nearest Adventure Spot", "distance_km": 250, "highway": "NH-5", "type": "adventure",
         "title": f"Adventure Trip from {home_city}", "cost": min(budget_inr * 0.8, 15000),
         "highlights": ["Trekking", "Camping", "River Rafting"], "food": "Campfire Meal"},
    ]

    city_destinations = destinations.get(home_city, default_destinations)

    recommendations = []
    for i, dest in enumerate(city_destinations[:5], 1):
        recommendations.append({
            "rank": i,
            "title": dest["title"],
            "destination": dest["destination"],
            "distance_km": dest["distance_km"],
            "highway": dest["highway"],
            "duration_days": duration_days,
            "estimated_cost_inr": round(dest["cost"], 0),
            "cost_per_person_inr": round(dest["cost"] / max(num_people, 1), 0),
            "destination_type": dest["type"],
            "best_for": f"Perfect for {group_type} trips with {interests_text(interests)}",
            "highlights": dest["highlights"],
            "best_season": season,
            "why_recommended": f"Great {dest['type']} destination reachable from {home_city} within your budget.",
            "difficulty_level": "easy",
            "must_try_food": dest["food"],
        })

    return {
        "home_city": home_city,
        "total_recommendations": 5,
        "recommendations": recommendations,
        "recommendation_tip": f"Best time to travel from {home_city} in {season} is early morning to avoid traffic.",
    }


def interests_text(interests: list) -> str:
    return ", ".join(interests) if interests else "general sightseeing"


# ── Main Function ─────────────────────────────────────────────────────────────

async def get_trip_recommendations(
    home_city: str,
    budget_inr: float,
    group_type: str = "friends",
    num_people: int = 2,
    duration_days: int = 3,
    season: str = "winter",
    interests: list[str] = None,
) -> dict:
    """
    Main function called from the router.
    Returns 5 personalized trip recommendations.
    """
    try:
        interests = interests or ["sightseeing"]

        if settings.gemini_api_key:
            prompt = build_recommender_prompt(
                home_city=home_city,
                budget_inr=budget_inr,
                group_type=group_type,
                num_people=num_people,
                duration_days=duration_days,
                season=season,
                interests=interests,
            )
            data = await call_groq_recommender(prompt)
        else:
            data = mock_recommendations(
                home_city=home_city,
                budget_inr=budget_inr,
                group_type=group_type,
                num_people=num_people,
                duration_days=duration_days,
                season=season,
                interests=interests,
            )

        return {
            "home_city": home_city,
            "budget_inr": budget_inr,
            "group_type": group_type,
            "num_people": num_people,
            "duration_days": duration_days,
            "season": season,
            "interests": interests,
            "recommendations": data.get("recommendations", []),
            "total_recommendations": data.get("total_recommendations", 0),
            "recommendation_tip": data.get("recommendation_tip", ""),
        }

    except Exception as e:
        raise RuntimeError(f"Trip recommendations failed: {e}")