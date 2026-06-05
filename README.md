# Ecosystem AI Services

Monorepo for AI microservices (ASR, TTS, OCR) with MCP tool support and REST API.

## Services

| Service | GPU | Model | Use case |
|---------|-----|-------|----------|
| **gateway** | No | FastAPI + MCP (SSE) | Routing, auth, task queue |
| **asr** | Yes | Whisper large-v3 / turbo | Speech → text |
| **tts-gpu** | Yes | XTTS-v2 / CosyVoice | Text → speech (high quality) |
| **tts-cpu** | No | Piper TTS | Text → speech (CPU scaling) |
| **surya** | Optional | Surya OCR | Image → text + layout |
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
├── nlp/              # NLP worker (optional Redis-based)
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
