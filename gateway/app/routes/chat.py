from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.container import container

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    response_format: dict | None = None


@router.post("/chat/completions")
async def chat_completions(body: ChatRequest):
    if body.stream:
        raise HTTPException(status_code=501, detail="Streaming not supported yet")
    messages = [m.model_dump(mode="json") for m in body.messages]
    try:
        return await container.llm.chat_completions(
            messages=messages,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            response_format=body.response_format,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
