"""
AI Journal Summarizer Service — RoadBuddy (Groq)
"""

import json
import httpx
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def build_summarizer_prompt(origin, destination, entries, total_days, total_cost_inr, group_type, num_people):
    entries_text = ""
    for i, entry in enumerate(entries, 1):
        entries_text += f"\nDay {entry.get('day', i)} — {entry.get('location', '')} | Mood: {entry.get('mood', '')} | {entry.get('text', '')} | Expenses: Rs {entry.get('expenses_inr', 0)}"

    return f"""You are RoadBuddy AI, a creative travel writer.
Trip: {origin} to {destination} | {total_days} days | {num_people} people ({group_type}) | Rs {total_cost_inr:.0f} total
{entries_text}

Generate a complete trip summary. Return ONLY valid JSON, no markdown:
{{
  "title": "Exciting trip title",
  "narrative": "3-4 paragraph first-person story. Vivid and emotional.",
  "highlights": ["Best moment", "Best food", "Most scenic spot", "Funniest moment"],
  "day_recaps": [
    {{"day": 1, "title": "Day title", "summary": "2-3 sentence recap.", "mood": "excited", "best_moment": "Best thing."}}
  ],
  "stats": {{
    "total_days": {total_days},
    "total_cost_inr": {total_cost_inr},
    "cost_per_person_inr": {total_cost_inr / max(num_people, 1):.0f},
    "places_visited": 0,
    "best_day": "Day 2",
    "mood_summary": "adventurous"
  }},
  "social_caption": "Fun Instagram caption under 150 chars with hashtags.",
  "tips_for_next_traveller": ["Tip 1", "Tip 2", "Tip 3"]
}}"""


async def call_groq_summarizer(prompt: str) -> dict:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 4000}
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        res.raise_for_status()
        text = res.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())


def mock_summary(origin, destination, entries, total_days, total_cost_inr, num_people):
    return {
        "title": f"From {origin} to {destination} — An Unforgettable Road Trip",
        "narrative": f"We set off from {origin} with excitement. Every turn brought surprises. By {destination}, we had memories no camera could capture.",
        "highlights": [f"Arriving at {destination} at sunset", "Roadside dhaba with dal baati", "Hidden temple", "Getting lost and finding a lake"],
        "day_recaps": [{"day": i+1, "title": f"Day {i+1} — {e.get('location', destination)}",
                        "summary": e.get("text", "A wonderful day.")[:150], "mood": e.get("mood", "excited"),
                        "best_moment": f"Exploring {e.get('location', destination)}"} for i, e in enumerate(entries)],
        "stats": {"total_days": total_days, "total_cost_inr": total_cost_inr,
                  "cost_per_person_inr": round(total_cost_inr / max(num_people, 1), 0),
                  "places_visited": len(entries), "best_day": "Day 2", "mood_summary": "adventurous"},
        "social_caption": f"Just back from {origin} to {destination}! 🚗✨ {total_days} days. #RoadBuddy #IndianRoadTrip",
        "tips_for_next_traveller": [f"Start early from {origin}", "Carry cash for tolls", "Highway dhabas are excellent"],
    }


async def summarize_trip_journal(origin, destination, entries, total_days, total_cost_inr=0, group_type="friends", num_people=2):
    try:
        if settings.groq_api_key and entries:
            data = await call_groq_summarizer(build_summarizer_prompt(origin, destination, entries, total_days, total_cost_inr, group_type, num_people))
        else:
            data = mock_summary(origin, destination, entries, total_days, total_cost_inr, num_people)
        return {"origin": origin, "destination": destination, "total_days": total_days, "num_people": num_people, "summary": data}
    except Exception as e:
        raise RuntimeError(f"Journal summarization failed: {e}")