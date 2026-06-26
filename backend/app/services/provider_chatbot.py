"""
AI Partner Helper Chatbot Service — RoadBuddy Partner (Groq)
"""

import httpx
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are RoadBuddy Partner Assistant, a helpful AI guide for transport operators, fleet managers, and cab/bus service providers on the RoadBuddy platform.
Your job is to help partners list vehicles, check user bookings, check stats/revenue, and manage settings.

Strict Constraints:
- You must ONLY answer questions directly related to the RoadBuddy Partner dashboard, partner services, and features (e.g., how to add a vehicle, how bookings work, how to check revenue, update settings, partner login/registration).
- If the user asks about ANY other topic (such as general knowledge, coding, tourist itinerary, hotel lists for riders, cooking, history, general questions, etc.), you MUST refuse to answer and respond EXACTLY with:
"I can only answer questions related to our app."
- Keep responses friendly, under 180 words, and use 1-2 emojis."""


def mock_partner_chat_response(message: str) -> str:
    msg_lower = message.lower()
    if "vehicle" in msg_lower or "add" in msg_lower or "car" in msg_lower or "bus" in msg_lower:
        return ("🚙 To add a vehicle, open the navigation sidebar menu (click the 3-line settings icon at the top-right), "
                "select **My Vehicles**, and click **+ Add Vehicle** on the top-right. Fill in the name, plate number, type, "
                "available seats, origin, destination, and fare details to activate it! 🚗")
    elif "booking" in msg_lower or "passenger" in msg_lower or "seat" in msg_lower:
        return ("📋 To view bookings, open the navigation sidebar and click **Bookings**. Here you can see passenger details, "
                "reserved seat maps (for route-based public vehicles), travel dates, contact numbers, and total fares. 💺")
    elif "revenue" in msg_lower or "money" in msg_lower or "earning" in msg_lower or "cost" in msg_lower or "fare" in msg_lower:
        return ("💰 Your total earnings and revenue are displayed on the main **Dashboard** stats cards, alongside the number of active "
                "vehicles, total bookings, and total seats booked. 📈")
    elif "setting" in msg_lower or "profile" in msg_lower or "edit" in msg_lower or "company" in msg_lower:
        return ("⚙️ To manage your profile or business details, open the navigation sidebar and click **Settings**. You can update your "
                "company name, contact person, alternate email, and notification preferences. 👤")
    elif any(word in msg_lower for word in ["help", "hi", "hello", "hey", "partner", "how to"]):
        return ("🚐 Welcome! I am your RoadBuddy Partner Assistant. I can guide you on how to list vehicles, manage bookings, check revenue, "
                "or update settings. How can I help you manage your fleet today? 😊")
    else:
        return "I can only answer questions related to our app."


async def call_groq_chat(messages: list[dict]) -> str:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        groq_messages.append({"role": msg["role"], "content": msg["content"]})
    payload = {"model": GROQ_MODEL, "messages": groq_messages, "temperature": 0.5, "max_tokens": 800}
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        if res.status_code != 200:
            print(f"Groq error: {res.status_code} — {res.text}")
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()


async def chat_with_provider_bot(message: str, history: list[dict] = None) -> dict:
    try:
        raw_history = history or []
        filtered_history = [h for h in raw_history if h.get("role") in ("user", "assistant")]
        truncated_history = filtered_history[-10:]
        
        messages = truncated_history + [{"role": "user", "content": message}]
        
        # Guard rails check for out-of-scope keywords before calling LLM
        msg_lower = message.lower()
        non_app_words = ["weather", "code", "python", "javascript", "history", "recipe", "cook", "capital", "president", "prime minister", "who is", "who was", "write a"]
        app_words = ["vehicle", "booking", "revenue", "setting", "earning", "partner", "roadbuddy", "profile", "logout", "login", "register"]
        
        is_out_of_scope = any(word in msg_lower for word in non_app_words) and not any(word in msg_lower for word in app_words)
        
        if is_out_of_scope:
            response_text = "I can only answer questions related to our app."
        elif settings.groq_api_key:
            try:
                response_text = await call_groq_chat(messages)
            except Exception as e:
                print(f"Groq provider chat failed: {e}. Falling back to mock response.")
                response_text = mock_partner_chat_response(message)
        else:
            response_text = mock_partner_chat_response(message)
            
        updated_history = messages + [{"role": "assistant", "content": response_text}]
        return {"response": response_text, "history": updated_history, "total_messages": len(updated_history)}
    except Exception as e:
        raise RuntimeError(f"Partner chat failed: {e}") from e
