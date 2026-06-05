from ..core.redis import push_task, get_task_result


TOOL_DEFINITIONS = [
    {
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
    },
    {
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
    },
    {
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
    },
]


async def handle_tool_call(name: str, arguments: dict) -> dict:
    if name == "transcribe_audio":
        task_id = await push_task("asr:queue", {
            "audio_url": arguments["audio_url"],
            "language": arguments.get("language", "auto"),
        })
    elif name == "synthesize_speech":
        task_id = await push_task("tts:queue", {
            "text": arguments["text"],
            "voice": arguments.get("voice", "default"),
            "model": arguments.get("model", "xtts-v2"),
        })
    elif name == "extract_text":
        task_id = await push_task("surya:queue", {
            "image_url": arguments["image_url"],
            "languages": arguments.get("languages", "en,ru").split(","),
        })
    else:
        raise ValueError(f"Unknown tool: {name}")

    result = await get_task_result(task_id)
    if result is None:
        return {"task_id": task_id, "status": "pending"}
    return result
