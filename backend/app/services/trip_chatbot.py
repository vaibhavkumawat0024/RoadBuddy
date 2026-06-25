"""
AI Trip Chatbot Service — RoadBuddy (Groq)
"""

import httpx
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are RoadBuddy AI, India's friendliest road trip assistant.
You have deep expertise in Indian road trips, highways, tourist destinations,
budget planning in INR, local food, dhabas, hotels, fuel costs, toll charges, and seasonal travel tips.

Rules:
- Always answer in the context of Indian travel
- Give realistic 2024-2025 INR prices
- Mention National Highway numbers for routes
- Break down budget (fuel + hotel + food + toll)
- Keep responses under 300 words
- Use 1-2 emojis per response
- Mention real place names only"""


def mock_chat_response(message: str) -> str:
    message_lower = message.lower()
    if any(word in message_lower for word in ["jaipur", "rajasthan"]):
        return ("🏰 Jaipur is a fantastic base for road trips! From Jaipur you can reach Ajmer (135 km via NH-48), "
                "Udaipur (393 km via NH-48), Ranthambore (180 km via NH-52). "
                "A 3-day Jaipur to Udaipur trip costs Rs 8,000-12,000 for 2 people. What type of trip are you planning? 🚗")
    elif any(word in message_lower for word in ["budget", "cost", "price"]):
        return ("💰 Rough budget breakdown: Fuel Rs 3-5 per km. Budget hotel Rs 800-1500/night. "
                "Food Rs 300-600 per person at dhabas. Tolls Rs 200-800. "
                "Tell me your origin, destination and days for an exact estimate! 🎯")
    elif any(word in message_lower for word in ["manali", "himachal", "mountain"]):
        return ("🏔️ Manali is amazing! Best time: Oct-Nov and Mar-Jun. From Delhi: 540 km via NH-44. "
                "Budget for 4 days: Rs 15,000-25,000 for 2 people. "
                "Top spots: Solang Valley, Rohtang Pass, Hadimba Temple. Want a detailed plan? 😊")
    else:
        return ("🚗 I'm RoadBuddy AI, your Indian road trip expert! "
                "I can help with trip planning, budget estimation, best routes, hotels, food, and seasonal tips. "
                "Try: 'Plan a 3-day trip from Jaipur to Udaipur for 2 people' 😊")


async def call_groq_chat(messages: list[dict]) -> str:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        groq_messages.append({"role": msg["role"], "content": msg["content"]})
    payload = {"model": GROQ_MODEL, "messages": groq_messages, "temperature": 0.8, "max_tokens": 1000}
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        if res.status_code != 200:
            print(f"Groq error: {res.status_code} — {res.text}")
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()


async def chat_with_roadbuddy(message: str, history: list[dict] = None) -> dict:
    try:
        raw_history = history or []
        # Filter to reject any role other than user/assistant (prevents system prompt injection)
        filtered_history = [h for h in raw_history if h.get("role") in ("user", "assistant")]
        # Apply sliding window of last 10 messages (5 turns)
        truncated_history = filtered_history[-10:]
        
        messages = truncated_history + [{"role": "user", "content": message}]
        if settings.groq_api_key:
            try:
                response_text = await call_groq_chat(messages)
            except Exception as e:
                print(f"Groq chat failed: {e}. Falling back to mock chat response.")
                response_text = mock_chat_response(message)
        else:
            response_text = mock_chat_response(message)
        updated_history = messages + [{"role": "assistant", "content": response_text}]
        return {"response": response_text, "history": updated_history, "total_messages": len(updated_history)}
    except Exception as e:
        raise RuntimeError(f"Chat failed: {e}") from e