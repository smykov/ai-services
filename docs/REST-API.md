# REST API

Base URL: `http://<gateway>:8000`

Authentication: `X-API-Key` header (optional, configured via `AI_API_KEYS`).

## Endpoints

### Health

```
GET /health
→ {"status": "ok"}
```

### Metrics

```
GET /metrics
→ {"uptime_seconds": 123, "service": "ecosystem-ai-services", "version": "0.1.0"}
```

### Transcribe Audio

```
POST /v1/audio/transcriptions

Form params:
  file     (file)    Audio file (WAV, MP3, etc.)
  language (string)  Language code: auto, ru, en (default: auto)
  model    (string)  Whisper model: turbo, large-v3 (default: turbo)
  async    (bool)    Async mode (default: false)

Sync response (200):
  {"text": "...", "task_id": "..."}

Async response (200):
  {"task_id": "...", "status": "queued"}
```

### Synthesize Speech

```
POST /v1/audio/speech

Form params:
  text   (string)  Text to synthesize
  voice  (string)  Voice name (default: default)
  model  (string)  TTS model: xtts-v2, cosyvoice (default: xtts-v2)
  async  (bool)    Async mode (default: false)

Response (200):
  {"audio_url": "http://...", "task_id": "..."}
```

### Extract Text (OCR)

```
POST /v1/ocr

Form params:
  file      (file)    Image file (PNG, JPG)
  languages (string)  Comma-separated (default: en,ru)
  async     (bool)    Async mode (default: false)

Response (200):
  {"text": "...", "blocks": [...], "task_id": "..."}
```

### Chat Completions (OpenAI-compatible)

```
POST /v1/chat/completions

Request body (JSON):
  model         (string)  Model name (default: qwen2.5:7b)
  messages      (array)   Chat messages: [{"role": "system|user|assistant", "content": "..."}]
  temperature   (float)   Sampling temperature (default: 0.1)
  max_tokens    (int)     Max tokens in response (optional)
  stream        (bool)    Streaming (not yet supported)
  response_format (obj)   JSON mode: {"type": "json_object"}

Response (200):
  Standard OpenAI chat completion format:
  {
    "id": "chatcmpl-xxx",
    "object": "chat.completion",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
  }

Notes:
  - If no system message is provided, a default NLP system prompt is injected
  - Set AI_LLM_BASE_URL=https://api.openai.com/v1 and AI_LLM_API_KEY=sk-... to use cloud
  - Set AI_LLM_MODEL=gpt-4o to switch models without code changes
```

### Task Status

```
GET /v1/tasks/{task_id}
→ {"task_id": "...", "status": "completed", "result": {...}}

GET /v1/tasks/{task_id}/download
→ {"download_url": "http://..."}
```

## Error Responses

| Status | Description |
|--------|-------------|
| 401 | Invalid API key |
| 413 | File too large |
| 422 | Validation error |
| 504 | Task timeout |
