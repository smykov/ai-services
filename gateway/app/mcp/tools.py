from collections.abc import Awaitable, Callable

from ..core.container import container
from ..core.redis import push_task

ToolHandler = Callable[..., Awaitable[dict]]

_registry: dict[str, tuple[dict, ToolHandler]] = {}


def register_tool(name: str, schema: dict):
    def decorator(handler: ToolHandler):
        _registry[name] = (schema, handler)
        return handler
    return decorator


def list_tools() -> list[dict]:
    return [schema for schema, _ in _registry.values()]


async def dispatch(name: str, arguments: dict) -> dict:
    entry = _registry.get(name)
    if entry is None:
        raise ValueError(f"Unknown tool: {name}")
    _, handler = entry
    return await handler(arguments)


@register_tool("transcribe_audio", {
    "name": "transcribe_audio",
    "description": "Transcribe audio file to text using Whisper ASR",
    "inputSchema": {
        "type": "object",
        "properties": {
            "audio_url": {"type": "string", "description": "URL to audio file"},
            "language": {"type": "string", "description": "Language code (auto, ru, en, etc.)", "default": "auto"},
        },
        "required": ["audio_url"],
    },
})
async def transcribe_audio(arguments: dict) -> dict:
    task_id = await push_task("asr:queue", {
        "audio_url": arguments["audio_url"],
        "language": arguments.get("language", "auto"),
    })
    return {"task_id": task_id, "status": "pending"}


@register_tool("synthesize_speech", {
    "name": "synthesize_speech",
    "description": "Generate speech audio from text using TTS",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to synthesize"},
            "voice": {"type": "string", "description": "Voice name", "default": "default"},
            "model": {"type": "string", "description": "TTS model (xtts-v2, cosyvoice, piper)", "default": "xtts-v2"},
        },
        "required": ["text"],
    },
})
async def synthesize_speech(arguments: dict) -> dict:
    task_id = await push_task("tts:queue", {
        "text": arguments["text"],
        "voice": arguments.get("voice", "default"),
        "model": arguments.get("model", "xtts-v2"),
    })
    return {"task_id": task_id, "status": "pending"}


@register_tool("preprocess_query", {
    "name": "preprocess_query",
    "description": "Send messages to NLP model for intent detection, entity extraction, and query preprocessing",
    "inputSchema": {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                        "content": {"type": "string"},
                    },
                    "required": ["role", "content"],
                },
                "description": "Chat messages in OpenAI format",
            },
            "temperature": {"type": "number", "description": "Sampling temperature", "default": 0.1},
        },
        "required": ["messages"],
    },
})
async def preprocess_query(arguments: dict) -> dict:
    messages = list(arguments["messages"])
    data = await container.llm.chat_completions(
        messages=messages,
        temperature=arguments.get("temperature"),
    )
    content = data["choices"][0]["message"]["content"]
    return {"content": content, "usage": data.get("usage", {})}


@register_tool("extract_text", {
    "name": "extract_text",
    "description": "Extract text from image using OCR (Surya)",
    "inputSchema": {
        "type": "object",
        "properties": {
            "image_url": {"type": "string", "description": "URL to image file"},
            "languages": {"type": "string", "description": "Comma-separated language codes", "default": "en,ru"},
        },
        "required": ["image_url"],
    },
})
async def extract_text(arguments: dict) -> dict:
    task_id = await push_task("surya:queue", {
        "image_url": arguments["image_url"],
        "languages": arguments.get("languages", "en,ru").split(","),
    })
    return {"task_id": task_id, "status": "pending"}
