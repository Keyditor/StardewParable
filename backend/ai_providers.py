import os
from typing import Optional


def resolve_provider(use_gemini: Optional[bool] = None, gemini_api_key: Optional[str] = None, openai_api_key: Optional[str] = None) -> str:
    gemini_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "") or "").strip()
    openai_key = (openai_api_key or os.getenv("OPENAI_API_KEY", "") or "").strip()

    if use_gemini is True:
        return "gemini"
    if gemini_key:
        return "gemini"
    if use_gemini is False:
        return "openai"
    if openai_key:
        return "openai"
    return "openai"


def build_llm_request(provider: str, model: str, api_key: str, api_base: str, temperature: float, system_prompt: str, user_message: str):
    if provider == "gemini":
        request_payload = {
            "contents": [
                {"parts": [{"text": user_message}]}
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            request_payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        base_url = api_base.rstrip("/")
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        return {
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "json": request_payload,
        }

    return {
        "url": f"{api_base.rstrip('/')}/chat/completions",
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "json": {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
    }
