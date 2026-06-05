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
