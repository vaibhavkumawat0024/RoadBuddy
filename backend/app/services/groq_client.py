import json
import re
import httpx
import asyncio
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


async def call_groq(prompt, system_prompt=None, temperature=0.5, max_tokens=3000, max_retries=3):
    if not settings.groq_api_key.strip():
        raise ValueError("GROQ_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key.strip()}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_exc = None
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(max_retries):
            try:
                res = await client.post(GROQ_URL, headers=headers, json=payload)
                if res.status_code == 429 or 500 <= res.status_code < 600:
                    await asyncio.sleep((attempt + 1) * 15)
                    continue
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"].strip()
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
            except Exception as e:
                last_exc = e
                await asyncio.sleep((attempt + 1) * 5)
    raise RuntimeError(f"Groq failed after {max_retries} retries: {last_exc}") from last_exc
