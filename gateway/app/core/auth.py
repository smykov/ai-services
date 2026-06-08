from fastapi import Header, HTTPException, Request, status

from .config import settings


async def verify_api_key(x_api_key: str = Header(None)):
    if not settings.api_keys:
        return None
    if x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


async def verify_mcp_token(request: Request):
    token = settings.mcp_bearer_token
    if not token:
        return None
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MCP token",
        )
    return token
