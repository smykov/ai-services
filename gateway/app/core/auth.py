from fastapi import Header, HTTPException, status

from .config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if not settings.api_keys:
        return None
    if x_api_key not in settings.api_keys.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key
