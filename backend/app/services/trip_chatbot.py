"""
AI Trip Chatbot Service — RoadBuddy
-------------------------------------
A conversational AI assistant for trip planning.
Supports multi-turn chat — remembers previous messages.
Users can ask things like:
  - "Plan a 3 day trip from Jaipur under Rs 5000"
  - "What are the best places to visit in Udaipur?"
  - "How much will it cost to drive from Jaipur to Manali?"
  - "Suggest a budget trip for 2 people this weekend"
"""

import httpx
from app.core.config import settings


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are RoadBuddy AI, India's friendliest and most knowledgeable road trip assistant.
You have deep expertise in:
  - Indian road trips and National Highways
  - Tourist destinations across all Indian states
  - Budget planning in Indian Rupees (INR)
  - Local food, dhabas, and restaurants
  - Hotels and stays for all budgets
  - Fuel costs, toll charges, and EV charging
  - Seasonal travel tips (summer, monsoon, winter)
  - Family, couple, friends, and solo travel

Your personality:
  - Friendly and enthusiastic about travel
  - Give specific, actionable advice
  - Always mention real place names, real costs in INR
  - Keep responses concise but helpful
  - Use simple language, avoid jargon
  - Add 1-2 emojis per response to keep it fun

Rules:
  - Always answer in the context of Indian travel
  - Give realistic 2024-2025 INR prices
  - If asked about a route, mention the National Highway number
  - If asked about budget, break it down (fuel + hotel + food + toll)
  - If the user's question is unclear, ask one clarifying question
  - Never make up places that don't exist
  - Keep each response under 300 words unless a detailed plan is requested
""".strip()


# ── Mock Response ─────────────────────────────────────────────────────────────

def mock_chat_response(message: str) -> str:
    message_lower = message.lower()

    if any(word in message_lower for word in ["jaipur", "rajasthan"]):
        return (
            "🏰 Jaipur is a fantastic base for road trips! "
            "From Jaipur you can easily reach Ajmer (135 km via NH-48), "
            "Pushkar (145 km), Udaipur (393 km via NH-48), "
            "and Ranthambore (180 km via NH-52). "
            "A 3-day Jaipur to Udaipur trip typically costs Rs 8,000-12,000 "
            "for 2 people including fuel, hotel, and food. "
            "What type of trip are you planning? 🚗"
        )
    elif any(word in message_lower for word in ["budget", "cost", "price", "cheap"]):
        return (
            "💰 Here's a rough budget breakdown for a typical Indian road trip: "
            "Fuel: Rs 3-5 per km for petrol cars. "
            "Budget hotel: Rs 800-1500 per night. "
            "Mid-range hotel: Rs 2000-4000 per night. "
            "Food per person per day: Rs 300-600 at dhabas, Rs 600-1200 at restaurants. "
            "Tolls: Rs 200-800 depending on route. "
            "Tell me your origin, destination and number of days — "
            "I'll give you an exact estimate! 🎯"
        )
    elif any(word in message_lower for word in ["manali", "himachal", "mountain", "hill"]):
        return (
            "🏔️ Manali is one of India's most popular road trip destinations! "
            "Best time to visit: October-November and March-June. "
            "Avoid July-August (heavy monsoon, landslides). "
            "From Delhi: 540 km via NH-44, takes 12-14 hours. "
            "From Chandigarh: 310 km via NH-21, takes 7-8 hours. "
            "Budget for 4 days: Rs 15,000-25,000 for 2 people. "
            "Top spots: Solang Valley, Rohtang Pass, Old Manali, Hadimba Temple. "
            "Want a detailed day-by-day plan? 😊"
        )
    elif any(word in message_lower for word in ["goa", "beach"]):
        return (
            "🏖️ Goa is perfect for a road trip! "
            "Best time: November to February (dry season). "
            "From Mumbai: 590 km via NH-66, takes 10-12 hours. "
            "From Pune: 450 km via NH-48, takes 8-9 hours. "
            "Budget for 4 days: Rs 20,000-35,000 for 2 people. "
            "Must visit: Baga Beach, Anjuna Flea Market, Old Goa Churches, "
            "Dudhsagar Falls (seasonal). "
            "Want me to plan the full route with stops? 🗺️"
        )
    else:
        return (
            "🚗 I'm RoadBuddy AI, your Indian road trip expert! "
            "I can help you with: \n"
            "• Trip planning and itineraries\n"
            "• Budget estimation in INR\n"
            "• Best routes and highways\n"
            "• Hotels, food, and fuel stops\n"
            "• Seasonal travel tips\n\n"
            "Try asking me: 'Plan a 3-day trip from Jaipur to Udaipur for 2 people' "
            "or 'What's the best time to visit Manali?' 😊"
        )


# ── Call Claude API ───────────────────────────────────────────────────────────

async def call_claude_chat(messages: list[dict]) -> str:
    """
    Call Claude API with full conversation history for multi-turn chat.
    messages = [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        res.raise_for_status()
        return res.json()["content"][0]["text"].strip()


# ── Main Function ─────────────────────────────────────────────────────────────

async def chat_with_roadbuddy(
    message: str,
    history: list[dict] = None,
) -> dict:
    """
    Main function called from the router.
    Accepts current message + full conversation history.
    Returns AI response + updated history.

    history format:
    [
        {"role": "user", "content": "Plan a trip to Manali"},
        {"role": "assistant", "content": "Sure! Here is a plan..."},
    ]
    """
    try:
        history = history or []

        # Build full message list with history + new message
        messages = history + [{"role": "user", "content": message}]

        if settings.anthropic_api_key:
            response_text = await call_claude_chat(messages)
        else:
            response_text = mock_chat_response(message)

        # Update history with new exchange
        updated_history = messages + [
            {"role": "assistant", "content": response_text}
        ]

        return {
            "response": response_text,
            "history": updated_history,
            "total_messages": len(updated_history),
        }

    except Exception as e:
        raise RuntimeError(f"Chat failed: {e}")