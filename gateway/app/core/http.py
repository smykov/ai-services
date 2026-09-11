import json
import logging

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

FALLBACK_ENCODINGS = ("cp1251", "cp866")


def _charset(request: Request) -> str | None:
    for part in request.headers.get("content-type", "").split(";")[1:]:
        name, _, value = part.partition("=")
        if name.strip().lower() == "charset":
            return value.strip().strip('"') or None
    return None


async def read_json(request: Request) -> dict:
    """Parse a JSON body, tolerating clients that send non-UTF-8 text.

    Starlette's request.json() assumes UTF-8 and raises UnicodeDecodeError (-> 500)
    when a Windows client posts Cyrillic in a legacy 8-bit codepage.
    """
    raw = await request.body()
    encodings = [e for e in (_charset(request), "utf-8", *FALLBACK_ENCODINGS) if e]

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        try:
            body = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Malformed JSON body: {exc}") from exc
        if encoding.lower().replace("-", "") != "utf8":
            logger.warning("Decoded request body as %s, client should send UTF-8", encoding)
        return body

    raise HTTPException(
        status_code=400,
        detail="Request body is not decodable text; send JSON encoded as UTF-8",
    )
