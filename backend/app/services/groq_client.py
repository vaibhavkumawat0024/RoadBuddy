import json
import re
import httpx
import asyncio
from app.core.config import settings

async def call_gemini_native(messages_or_prompt, system_prompt=None, temperature=0.7, max_tokens=4000) -> str:
    api_key = settings.gemini_api_key.strip() if settings.gemini_api_key else ""
    if not api_key:
        api_key = settings.groq_api_key.strip() if settings.groq_api_key else ""
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GROQ_API_KEY is not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    contents = []
    system_instr = system_prompt

    if isinstance(messages_or_prompt, str):
        contents.append({"role": "user", "parts": [{"text": messages_or_prompt}]})
    elif isinstance(messages_or_prompt, list):
        for msg in messages_or_prompt:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                system_instr = content
            else:
                gemini_role = "model" if role in ["assistant", "model"] else "user"
                contents.append({"role": gemini_role, "parts": [{"text": content}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }
    if system_instr:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instr}]
        }

    last_exc = None
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                res = await client.post(url, json=payload)
                if res.status_code == 429:
                    await asyncio.sleep((attempt + 1) * 3)
                    continue
                res.raise_for_status()
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text
            except Exception as e:
                last_exc = e
                await asyncio.sleep((attempt + 1) * 1)
    raise RuntimeError(f"Gemini call failed after 3 retries: {last_exc}") from last_exc


async def call_groq(prompt, system_prompt=None, temperature=0.5, max_tokens=3000, max_retries=3):
    # This maintains backward compatibility for callers expecting JSON return
    content = await call_gemini_native(prompt, system_prompt, temperature, max_tokens)
    
    if content.startswith("```"):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if m:
            content = m.group(1).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m2 = re.search(r"(\{[\s\S]*\})", content)
        if m2:
            return json.loads(m2.group(1))
        raise
