import json
import logging
import os
from typing import Any, Dict, Optional
try:
    from dotenv import load_dotenv
except ImportError:  
    def load_dotenv() -> bool:
        return False
load_dotenv()
logger = logging.getLogger(__name__)
class LLMClient:
    def __init__(self) -> None:
        self.model = os.getenv("SHOPNEXAI_LLM_MODEL", "gpt-4o-mini")
        self._client = None
        api_key = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=api_key)
            except Exception as exc:  
                logger.warning("OpenAI client unavailable: %s", exc)
    @property
    def available(self) -> bool:
        return self._client is not None
    async def json_completion(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            value = json.loads(content)
            return value if isinstance(value, dict) else None
        except Exception as exc:  
            logger.warning("ShopNexAI JSON LLM call failed: %s", exc)
            return None
    async def text_completion(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[str]:
        if not self._client:
            return None
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=400,
            )
            return (response.choices[0].message.content or "").strip() or None
        except Exception as exc:  
            logger.warning("ShopNexAI text LLM call failed: %s", exc)
            return None
