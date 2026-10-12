# Ecosystem AI Services

Monorepo for AI microservices (ASR, TTS, OCR, talking head) with MCP tool support and REST API.

## Services

| Service | GPU | Model | Use case |
|---------|-----|-------|----------|
| **gateway** | No | FastAPI + MCP (SSE) | Routing, auth, task queue |
| **asr** | Yes | Whisper large-v3 / turbo | Speech → text |
| **tts-gpu** | Yes | XTTS-v2 / CosyVoice | Text → speech (high quality) |
| **tts-cpu** | No | Piper TTS | Text → speech (CPU scaling) |
| **surya** | Optional | Surya OCR | Image → text + layout |
| **avatar** | Yes | MuseTalk 1.5 + GFPGAN | Face video + speech → talking-head video |
| **ollama** | Yes | Qwen2.5 7B | LLM inference (NLP, intent, chat) |

## Architecture

```
Client → gateway (REST / MCP) → Redis Queue → Worker → Result → Redis Pub/Sub → Response
```

- **Sync mode**: gateway subscribes to result channel before pushing task, waits with timeout
- **Async mode**: returns `task_id` immediately, client polls `GET /v1/tasks/{id}`
- **Files**: uploaded to MinIO before task creation; workers read from MinIO
- **MCP**: SSE transport with tool definitions, Bearer token auth

## Quick Start (Demo)

```bash
docker compose -f deploy/docker-compose.demo.yml up -d
```

Gateway: http://localhost:8000 — Docs: http://localhost:8000/docs

## API

See [docs/REST-API.md](docs/REST-API.md) and [docs/MCP-PROTOCOL.md](docs/MCP-PROTOCOL.md).

## Project Structure

```
├── gateway/          # FastAPI + MCP SSE endpoint
├── asr/              # Whisper ASR worker
├── tts-gpu/          # GPU TTS worker (XTTS-v2)
├── tts-cpu/          # CPU TTS worker (Piper)
├── surya/            # Surya OCR worker
├── avatar/           # Talking-head worker (MuseTalk lip-sync, GFPGAN)
├── shared/           # Common: WorkerBase, MinIO uploader
├── deploy/           # Docker Compose, systemd service
└── .github/workflows/# CI + Deploy pipelines
```

## Configuration

All settings via environment variables with `AI_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `AI_MINIO_ENDPOINT` | `minio:9000` | MinIO endpoint |
| `AI_MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `AI_MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `AI_MINIO_BUCKET` | `ai-services` | MinIO bucket |
| `AI_API_KEYS` | `` | Comma-separated API keys |
| `AI_MCP_BEARER_TOKEN` | `` | MCP Bearer token |
| `AI_MAX_UPLOAD_SIZE_MB` | `100` | Max file upload size |
| `AI_TASK_TIMEOUT` | `60` | Sync mode timeout (s) |
| `AI_LLM_BASE_URL` | `http://ollama:11434/v1` | LLM API base URL |
| `AI_LLM_API_KEY` | `` | LLM API key (for cloud providers) |
| `AI_LLM_MODEL` | `qwen2.5:7b` | LLM model name |
| `AI_DEFAULT_NLP_SYSTEM_PROMPT` | `You are a helpful...` | Default system prompt injected when missing |

## Talking head (avatar)

`POST /v1/video/talking-head` lip-syncs a short face video (or a photo) to any speech audio — see [docs/REST-API.md](docs/REST-API.md#talking-head-video).

- **GPU memory:** models load on the first task and leave the GPU after `AVATAR_IDLE_UNLOAD_S` idle seconds (default 300); renders run one at a time. Peak use is about 6–8 GB with restoration on.
- **Speed:** a prepared face is cached by content hash (`face_id`), and only frames with speech go through the lip-sync network — pauses show cached idle frames, so long videos with pauses cost roughly their speaking time.
- **Weights** are downloaded into the `avatar_models` volume on first start (about 4 GB) from their upstream sources and are not redistributed here: MuseTalk (MIT), sd-vae-ft-mse (CreativeML OpenRAIL-M), Whisper tiny (MIT), DWPose (Apache-2.0), face-parsing BiSeNet (MIT), GFPGAN (Apache-2.0). Check each license before commercial use.
- **Consent:** use only faces of people who agreed to it, and do not present generated video as a real recording.

## Security

Authentication is off when `AI_API_KEYS` and `AI_MCP_BEARER_TOKEN` are empty, which is the demo default. Set both before exposing the gateway beyond localhost, and change the MinIO credentials from `minioadmin`.

## Development

```bash
pip install -r gateway/requirements.txt
cd gateway && AI_REDIS_URL=redis://localhost:6379/0 uvicorn app.main:app --reload
```

### Tests

```bash
pip install pytest httpx
pytest gateway/tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
