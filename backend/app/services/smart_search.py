"""
AI Smart Search Service — RoadBuddy
-------------------------------------
Takes a natural language query and extracts
smart filters to search community routes.

Examples:
  "beach trip under 5000"
  "family trip to hill station 3 days"
  "weekend trip from Jaipur under 10000"
  "solo trip to Rajasthan heritage"
"""

import json
import httpx
from app.core.config import settings

GROQ_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_MODEL = "gemini-1.5-flash"


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_search_prompt(query: str) -> str:
    return f"""You are RoadBuddy AI, an Indian travel search engine.
A user typed this search query: "{query}"

Extract travel filters from this query and return ONLY valid JSON, no markdown:
{{
  "understood_query": "What you understood from the query in 1 sentence.",
  "destination": "Specific destination if mentioned, else null",
  "destination_type": "One of: beach, hill_station, heritage, desert, forest, city, religious, adventure, or null",
  "origin": "Origin city if mentioned, else null",
  "max_budget_inr": 0,
  "duration_days": 0,
  "group_type": "One of: family, couple, friends, solo, or null",
  "season": "One of: summer, monsoon, winter, or null",
  "keywords": ["list", "of", "important", "keywords", "from", "query"],
  "suggested_destinations": ["3 real Indian destinations that match this query"],
  "search_tips": "One helpful tip for this type of trip in India."
}}

Rules:
- max_budget_inr: extract number from query. If not mentioned use 0
- duration_days: extract number of days. If "weekend" use 2. If not mentioned use 0
- destination_type: guess from context (e.g. "hill station" → hill_station, "beach" → beach)
- suggested_destinations: always suggest 3 real Indian places that match
- Be smart — "under 5k" means max_budget_inr: 5000
- "family" or "kids" means group_type: family
- "couple" or "honeymoon" means group_type: couple
- "solo" means group_type: solo
"""


# ── Call Groq API ─────────────────────────────────────────────────────────────

async def call_groq_search(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.gemini_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1000,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())


# ── Mock Response ─────────────────────────────────────────────────────────────

def mock_search(query: str) -> dict:
    query_lower = query.lower()

    if "beach" in query_lower or "goa" in query_lower:
        return {
            "understood_query": "Looking for a beach trip in India.",
            "destination": "Goa",
            "destination_type": "beach",
            "origin": None,
            "max_budget_inr": 10000,
            "duration_days": 3,
            "group_type": None,
            "season": "winter",
            "keywords": ["beach", "sea", "sand", "coastal"],
            "suggested_destinations": ["Goa", "Kovalam Kerala", "Puri Odisha"],
            "search_tips": "Best beach trips in India are from November to February.",
        }
    elif "hill" in query_lower or "mountain" in query_lower or "manali" in query_lower:
        return {
            "understood_query": "Looking for a hill station trip.",
            "destination": None,
            "destination_type": "hill_station",
            "origin": None,
            "max_budget_inr": 15000,
            "duration_days": 4,
            "group_type": None,
            "season": "summer",
            "keywords": ["hills", "mountains", "cool", "scenic"],
            "suggested_destinations": ["Manali Himachal Pradesh", "Ooty Tamil Nadu", "Munnar Kerala"],
            "search_tips": "Hill stations are best visited in summer (April-June) to escape the heat.",
        }
    elif "heritage" in query_lower or "rajasthan" in query_lower or "fort" in query_lower:
        return {
            "understood_query": "Looking for a heritage or cultural trip.",
            "destination": "Rajasthan",
            "destination_type": "heritage",
            "origin": None,
            "max_budget_inr": 12000,
            "duration_days": 5,
            "group_type": None,
            "season": "winter",
            "keywords": ["heritage", "fort", "palace", "culture", "history"],
            "suggested_destinations": ["Jaipur Rajasthan", "Udaipur Rajasthan", "Jodhpur Rajasthan"],
            "search_tips": "October to March is the best time for Rajasthan heritage trips.",
        }
    elif "family" in query_lower or "kids" in query_lower:
        return {
            "understood_query": "Looking for a family-friendly trip.",
            "destination": None,
            "destination_type": None,
            "origin": None,
            "max_budget_inr": 20000,
            "duration_days": 3,
            "group_type": "family",
            "season": None,
            "keywords": ["family", "kids", "children", "safe"],
            "suggested_destinations": ["Shimla Himachal Pradesh", "Mysore Karnataka", "Coorg Karnataka"],
            "search_tips": "For family trips, choose destinations with good road connectivity and clean hotels.",
        }
    else:
        return {
            "understood_query": f"Looking for a trip matching: {query}",
            "destination": None,
            "destination_type": None,
            "origin": None,
            "max_budget_inr": 10000,
            "duration_days": 3,
            "group_type": None,
            "season": None,
            "keywords": query.lower().split(),
            "suggested_destinations": ["Jaipur Rajasthan", "Manali Himachal Pradesh", "Goa"],
            "search_tips": "Try being more specific — mention destination, budget, or number of days.",
        }


# ── Main Function ─────────────────────────────────────────────────────────────

async def smart_search(query: str) -> dict:
    """
    Main function called from the router.
    Takes natural language query and returns extracted filters + suggestions.
    """
    try:
        if settings.gemini_api_key:
            prompt = build_search_prompt(query)
            filters = await call_groq_search(prompt)
        else:
            filters = mock_search(query)

        return {
            "query": query,
            "filters": filters,
            "message": f"Found filters for: {filters.get('understood_query', query)}",
        }

    except Exception as e:
        raise RuntimeError(f"Smart search failed: {e}")