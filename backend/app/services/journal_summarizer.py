"""
AI Journal Summarizer Service — RoadBuddy
------------------------------------------
Takes daily journal entries from a trip and generates:
  - A beautiful narrative trip summary
  - Key highlights and best moments
  - Total stats (distance, cost, places visited)
  - A short shareable social media caption
  - A day-by-day recap
"""

import httpx
from app.core.config import settings


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_summarizer_prompt(
    origin: str,
    destination: str,
    entries: list[dict],
    total_days: int,
    total_cost_inr: float,
    group_type: str,
    num_people: int,
) -> str:

    # Format journal entries for the prompt
    entries_text = ""
    for i, entry in enumerate(entries, 1):
        entries_text += f"""
Day {entry.get('day', i)} — {entry.get('date', 'Unknown date')}
Location : {entry.get('location', 'Unknown')}
Mood     : {entry.get('mood', 'neutral')}
Entry    : {entry.get('text', 'No entry written.')}
Expenses : Rs {entry.get('expenses_inr', 0)}
---"""

    return f"""
You are RoadBuddy AI, a creative travel writer who specializes in
turning raw travel journal entries into beautiful, engaging trip summaries.

Trip details:
- Route       : {origin} to {destination}
- Duration    : {total_days} days
- Travellers  : {num_people} people ({group_type})
- Total spent : Rs {total_cost_inr:.0f}

Journal entries:
{entries_text}

Based on these journal entries, generate a complete trip summary.

Return ONLY a valid JSON object in this exact shape, nothing else:
{{
  "title": "An exciting trip title (e.g. 'Pink City to Lake City — A Royal Rajasthan Road Trip')",
  "narrative": "A beautifully written 3-4 paragraph story of the entire trip. Write in first person. Make it vivid, emotional, and engaging. Mention specific places, food, and moments from the journal entries.",
  "highlights": [
    "Best moment or place from the trip",
    "Most memorable food experience",
    "Most scenic spot visited",
    "Funniest or most unexpected moment"
  ],
  "day_recaps": [
    {{
      "day": 1,
      "title": "Short catchy title for this day",
      "summary": "2-3 sentence recap of this day based on the journal entry.",
      "mood": "excited",
      "best_moment": "The single best thing about this day."
    }}
  ],
  "stats": {{
    "total_days": {total_days},
    "total_cost_inr": {total_cost_inr},
    "cost_per_person_inr": {total_cost_inr / max(num_people, 1):.0f},
    "places_visited": 0,
    "best_day": "Day number that was the best based on mood and entries",
    "mood_summary": "Overall mood of the trip in one word"
  }},
  "social_caption": "A short, fun Instagram/WhatsApp caption for this trip. Include 3-4 relevant hashtags like #RoadBuddy #RajasthanRoadTrip etc. Under 150 characters.",
  "tips_for_next_traveller": [
    "Practical tip based on this trip experience",
    "Another useful tip",
    "One more tip"
  ]
}}

Writing rules:
- Write the narrative in first person ("We drove...", "I felt...", "The view was...")
- Make it emotional and engaging — not just a list of facts
- Reference specific details from the journal entries
- Keep each day recap concise but vivid
- Social caption should be fun and shareable
- Tips should be genuinely useful for future travellers on this route
""".strip()


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude_summarizer(prompt: str) -> dict:
    """Call Claude API and return parsed summary JSON."""
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
        import json
        text = res.json()["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())


# ── Mock Summary ──────────────────────────────────────────────────────────────

def mock_summary(
    origin: str,
    destination: str,
    entries: list[dict],
    total_days: int,
    total_cost_inr: float,
    num_people: int,
) -> dict:
    return {
        "title": f"From {origin} to {destination} — An Unforgettable Indian Road Trip",
        "narrative": (
            f"We set off from {origin} with nothing but excitement and a full tank of fuel. "
            f"The open road stretched ahead of us, lined with golden fields and distant hills. "
            f"Every turn brought a new surprise — a roadside dhaba with the most amazing dal baati, "
            f"a hidden temple that wasn't on any map, and sunsets that painted the sky in shades of orange and pink. "
            f"\n\nBy the time we reached {destination}, we had collected memories that no camera could fully capture. "
            f"The lake shimmered in the evening light as we checked into our hotel, "
            f"exhausted but deeply satisfied. {destination} welcomed us with its royal charm "
            f"and we spent the next two days losing ourselves in its palaces, markets, and flavours. "
            f"\n\nThe return journey felt different — quieter, more reflective. "
            f"We talked about our favourite moments, laughed at the wrong turns, "
            f"and promised ourselves we'd do this again soon. "
            f"A road trip is never just about the destination. It's about everything in between."
        ),
        "highlights": [
            f"Arriving at {destination} at sunset — absolutely breathtaking",
            "That roadside dhaba with unlimited dal baati for Rs 150",
            "The hidden temple 5km off the highway that locals recommended",
            "Getting lost and accidentally finding a beautiful lake",
        ],
        "day_recaps": [
            {
                "day": i + 1,
                "title": f"Day {i + 1} — {entry.get('location', destination)}",
                "summary": (
                    entry.get("text", "A wonderful day of travel and exploration.")[:150]
                    + "..."
                ),
                "mood": entry.get("mood", "excited"),
                "best_moment": f"Exploring {entry.get('location', destination)}",
            }
            for i, entry in enumerate(entries)
        ],
        "stats": {
            "total_days": total_days,
            "total_cost_inr": total_cost_inr,
            "cost_per_person_inr": round(total_cost_inr / max(num_people, 1), 0),
            "places_visited": len(entries),
            "best_day": "Day 2",
            "mood_summary": "adventurous",
        },
        "social_caption": (
            f"Just got back from the most amazing road trip — {origin} to {destination}! 🚗✨ "
            f"{total_days} days, {num_people} people, countless memories. "
            f"#RoadBuddy #IndianRoadTrip #RajasthanDiaries #TravelIndia"
        ),
        "tips_for_next_traveller": [
            f"Start early from {origin} — before 7am to avoid highway traffic",
            "Carry cash for toll plazas — not all accept UPI",
            f"The dhabas on NH-48 are excellent — don't skip lunch on the highway",
        ],
    }


# ── Main Function ─────────────────────────────────────────────────────────────

async def summarize_trip_journal(
    origin: str,
    destination: str,
    entries: list[dict],
    total_days: int,
    total_cost_inr: float = 0,
    group_type: str = "friends",
    num_people: int = 2,
) -> dict:
    """
    Main function called from the router.
    Takes journal entries and returns a beautiful AI-generated trip summary.

    entries format:
    [
        {
            "day": 1,
            "date": "2025-12-01",
            "location": "Ajmer",
            "mood": "excited",
            "text": "We left Jaipur early morning...",
            "expenses_inr": 2400
        }
    ]
    """
    try:
        if settings.anthropic_api_key and entries:
            prompt = build_summarizer_prompt(
                origin=origin,
                destination=destination,
                entries=entries,
                total_days=total_days,
                total_cost_inr=total_cost_inr,
                group_type=group_type,
                num_people=num_people,
            )
            data = await call_claude_summarizer(prompt)
        else:
            data = mock_summary(
                origin=origin,
                destination=destination,
                entries=entries,
                total_days=total_days,
                total_cost_inr=total_cost_inr,
                num_people=num_people,
            )

        return {
            "origin": origin,
            "destination": destination,
            "total_days": total_days,
            "num_people": num_people,
            "summary": data,
        }

    except Exception as e:
        raise RuntimeError(f"Journal summarization failed: {e}")