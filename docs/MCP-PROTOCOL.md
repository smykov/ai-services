# MCP Protocol

Endpoint: `GET /mcp` (SSE) / `POST /mcp` (JSON-RPC)

Authentication: `Authorization: Bearer <token>` header (configurable via `AI_MCP_BEARER_TOKEN`).

## Transport

Server-Sent Events (SSE) according to MCP specification:

1. Client connects to `GET /mcp` → receives SSE stream with `connected` event
2. Client sends JSON-RPC messages via `POST /mcp`
3. Server responds inline (request/response pattern)

## Initialization

```json
→ {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
← {"jsonrpc": "2.0", "id": 1, "result": {
    "protocolVersion": "0.1.0",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "ecosystem-ai-services", "version": "0.1.0"}
  }}
```

## Tools

### transcribe_audio

```json
→ {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
    "name": "transcribe_audio",
    "arguments": {"audio_url": "http://...", "language": "ru"}
  }}
← {"jsonrpc": "2.0", "id": 2, "result": {
    "content": [{"type": "text", "text": "{\"task_id\": \"...\", \"status\": \"pending\"}"}]
  }}
```

### synthesize_speech

```json
→ {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
    "name": "synthesize_speech",
    "arguments": {"text": "Hello", "voice": "default", "model": "xtts-v2"}
  }}
```

### extract_text

```json
→ {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
    "name": "extract_text",
    "arguments": {"image_url": "http://...", "languages": "en,ru"}
  }}
```

All tools return `{"task_id": "...", "status": "pending"}` — poll `GET /v1/tasks/{id}` for result.
