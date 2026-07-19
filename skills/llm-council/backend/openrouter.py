"""OpenRouter API client with parallel querying and smart timeout."""

import asyncio
import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL, MODEL_TIMEOUT


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = MODEL_TIMEOUT
) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": model, "messages": messages}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data['choices'][0]['message']
            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details')
            }
    except Exception as e:
        print(f"  ✗ {model}: {type(e).__name__}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    async def query_with_timeout(model):
        try:
            result = await asyncio.wait_for(query_model(model, messages), timeout=MODEL_TIMEOUT)
            if result:
                print(f"  ✓ {model}")
            else:
                print(f"  ✗ {model}: empty response")
            return model, result
        except asyncio.TimeoutError:
            print(f"  ✗ {model}: timeout ({MODEL_TIMEOUT}s)")
            return model, None

    tasks = [query_with_timeout(m) for m in models]
    results_list = await asyncio.gather(*tasks)
    return dict(results_list)
