import base64
import json
import logging

from httpx import AsyncClient, HTTPError, HTTPStatusError, RequestError

from .config import settings

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT = (
    "Analyze this image and respond ONLY with valid JSON (no markdown, no explanation):\n"
    '{"type": "receipt|document|person|other", "has_pii": true|false, "description": "brief 1-sentence description"}\n\n'
    "Type definitions:\n"
    '- "receipt": shopping receipt, invoice, payment bill\n'
    '- "document": passport, ID card, contract, certificate, official form\n'
    '- "person": photo containing a human face or full body\n'
    '- "other": any other content\n\n'
    "has_pii = true if image contains personal data: name, address, phone, ID number, face, signature, etc."
)


class LLMService:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        default_system_prompt: str | None = None,
        timeout: float = 120,
    ):
        self._base_url = (base_url or settings.llm_base_url).rstrip("/")
        self._api_key = api_key if api_key is not None else settings.llm_api_key
        self._model = model or settings.llm_model
        self._default_system_prompt = (
            default_system_prompt if default_system_prompt is not None else settings.default_nlp_system_prompt
        )
        self._client = AsyncClient(timeout=timeout)

    async def close(self):
        await self._client.aclose()

    def _inject_system_prompt(self, messages: list[dict]) -> list[dict]:
        has_system = any(m["role"] == "system" for m in messages)
        if not has_system and self._default_system_prompt:
            return [{"role": "system", "content": self._default_system_prompt}, *messages]
        return messages

    def _build_headers(self) -> dict:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
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
            "model": model or self._model,
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
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._build_headers(),
            )
            resp.raise_for_status()
            return resp.json()
        except HTTPStatusError as e:
            status = e.response.status_code
            detail = e.response.text[:500]
            logger.warning("LLM backend error %s: %.200s", status, detail)
            raise RuntimeError(f"LLM backend error ({status}): {detail}")
        except RequestError as e:
            logger.error("LLM backend connection failed: %s", e)
            raise RuntimeError(f"LLM backend unavailable: {e}") from e
        except HTTPError as e:
            logger.error("LLM backend error: %s", e)
            raise RuntimeError(f"LLM backend error: {e}")
        except Exception as e:
            logger.error("LLM backend unexpected error: %s", e)
            raise RuntimeError("LLM backend internal error") from e

    async def classify_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> dict:
        b64 = base64.b64encode(image_bytes).decode()
        data_url = f"data:{mime_type};base64,{b64}"
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": _CLASSIFY_PROMPT},
                ],
            }
        ]
        payload = {
            "model": settings.vision_model,
            "messages": messages,
            "temperature": 0.1,
            "stream": False,
        }
        try:
            resp = await self._client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=self._build_headers(),
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except HTTPStatusError as e:
            status = e.response.status_code
            detail = e.response.text[:500]
            logger.warning("Vision LLM error %s: %.200s", status, detail)
            raise RuntimeError(f"Vision LLM backend error ({status}): {detail}") from e
        except RequestError as e:
            raise RuntimeError(f"Vision LLM unavailable: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"Vision LLM returned invalid JSON: {e}") from e
        except Exception as e:
            raise RuntimeError("Vision LLM internal error") from e
