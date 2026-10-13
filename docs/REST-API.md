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
  speaker_wav  (file | base64 string)
                   Reference voice sample for XTTS voice cloning (optional).
                   multipart: file field; JSON/form: base64-encoded audio.
                   Without it the default voice is used.
                   Errors: 413 sample too large, 422 empty or invalid base64

Response (200):
  {"audio_url": "http://...", "task_id": "..."}
```


### Talking-head video

```
POST /v1/video/talking-head   (multipart/form-data)

Form params:
  audio              (file)    Speech to lip-sync; any format ffmpeg reads (required)
  face               (file)    Face video or photo: looking at the camera, mouth closed;
                               the first 30 s are used, played forward and backward in a loop
  face_id            (string)  Reuse a face prepared by an earlier call (returned in the result)
                               instead of uploading `face` again — one of the two is required
  restore            (bool)    Restore the face with GFPGAN (default: true) — sharper mouth and beard
  restore_weight     (float)   GFPGAN strength 0..1 (default: 0.5); higher is sharper, skin gets smoother
  parsing_mode       (string)  Blend border: jaw | raw (default: jaw)
  left_cheek_width   (int)     Cheek width of the blended area, 0..200 (default: 90)
  right_cheek_width  (int)     (default: 90)
  extra_margin       (int)     Extra pixels below the chin, 0..60 (default: 10)
  max_side           (int)     Longer side of the output, 256..1920 px (default: 720)
  async              (bool)    Return task_id immediately (default: true)

Response (async):
  {"task_id": "...", "status": "queued"}

GET /v1/tasks/{task_id} while rendering:
  {"task_id": "...", "status": "processing",
   "progress": {"stage": "rendering", "frames_done": 1200, "frames_total": 4500, "elapsed_s": 61.0}}

GET /v1/tasks/{task_id} when done:
  {"status": "completed", "result": {"object_name": "avatar/<task_id>.mp4", "face_id": "<32 hex>",
   "frames": 4500, "speech_frames": 2100, "seconds": 180.0, "width": 720, "height": 720, "render_s": 240.5}}
GET /v1/tasks/{task_id}/download → {"download_url": "..."}   (MP4, H.264 + AAC, 25 fps)

Errors: 413 file too large, 422 neither face nor face_id / invalid option,
        502 worker failed (sync mode); in async mode a failure is {"result": {"error": "..."}}
```

Face preparation (landmarks, masks, idle frames) takes about a minute and is cached per face and
option set; the result's `face_id` skips it on later calls. Results are kept for 24 hours.

### Classify Image

```
POST /v1/classify

Form params:
  file  (file)  Image file (JPEG, PNG, WebP)

Response (200):
  {
    "type":        "receipt" | "document" | "person" | "other",
    "has_pii":     true | false,
    "description": "Brief description of image content"
  }

type values:
  receipt   Shopping receipt, invoice, payment bill
  document  Passport, ID card, contract, certificate, official form
  person    Photo containing a human face or full body
  other     Any other content (product, screenshot, landscape, etc.)

has_pii = true if the image contains personal data:
  name, address, phone number, ID/passport number, face, signature

Model: qwen2.5vl:7b (local Ollama, multimodal vision; set by `AI_VISION_MODEL`)

Errors:
  415  Unsupported image format (use JPEG, PNG, or WebP)
  413  File too large
  503  Vision model unavailable
```

**Example — curl:**
```bash
curl -X POST http://localhost:8000/v1/classify   -H "X-API-Key: <key>"   -F "file=@receipt.jpg"
# → {"type":"receipt","has_pii":true,"description":"A store receipt showing customer name and items purchased."}
```

**Use as OCR pre-filter:**
1. Call `/v1/classify` on the uploaded image
2. If `has_pii=true` and type is `document` or `receipt` → decide: mask or reject
3. Call `/v1/ocr` for text extraction (works regardless of classify result — fail-open)

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
