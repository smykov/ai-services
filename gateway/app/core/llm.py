from httpx import AsyncClient, HTTPError

from .config import settings


class LLMService:
    def __init__(self):
        self._client = AsyncClient(timeout=120)

    async def close(self):
        await self._client.aclose()

    def _inject_system_prompt(self, messages: list[dict]) -> list[dict]:
        has_system = any(m["role"] == "system" for m in messages)
        if not has_system and settings.default_nlp_system_prompt:
            return [{"role": "system", "content": settings.default_nlp_system_prompt}, *messages]
        return messages

    def _build_headers(self) -> dict:
        if settings.llm_api_key:
            return {"Authorization": f"Bearer {settings.llm_api_key}"}
        return {}

    async def chat_completions(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> dict:
        messages = self._inject_system_prompt(messages)

        payload = {
            "model": model or settings.llm_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.1,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            resp = await self._client.post(
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=self._build_headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except HTTPError as e:
            detail = e.response.text[:500] if e.response else str(e)
            raise RuntimeError(f"LLM backend error ({e.response.status_code}): {detail}")
        except Exception as e:
            raise RuntimeError("LLM backend unavailable")
