import asyncio
import json
import uuid

from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from ..core.auth import verify_mcp_token
from ..core.config import settings
from .tools import dispatch, list_tools


async def sse_endpoint(request):
    await verify_mcp_token(request)
    client_id = str(uuid.uuid4())

    async def event_stream():
        yield f"event: connected\ndata: {json.dumps({'client_id': client_id})}\n\n"
        while True:
            await asyncio.sleep(30)
            yield "event: ping\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def message_endpoint(request):
    await verify_mcp_token(request)
    body = await request.json()
    method = body.get("method")
    msg_id = body.get("id")

    if method == "initialize":
        return _json_resp(msg_id, {
            "protocolVersion": "0.1.0",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": settings.mcp_server_name,
                "version": settings.mcp_server_version,
            },
        })

    if method == "tools/list":
        return _json_resp(msg_id, {"tools": list_tools()})

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            result = await dispatch(name, arguments)
            return _json_resp(msg_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            })
        except ValueError as e:
            return _json_error(msg_id, -32602, str(e))
        except Exception as e:
            return _json_error(msg_id, -32000, str(e))

    return _json_error(msg_id, -32601, f"Method not found: {method}")


def _json_resp(msg_id, result):
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _json_error(msg_id, code: int, message: str):
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


routes = [
    Route("/mcp", endpoint=sse_endpoint, methods=["GET"]),
    Route("/mcp", endpoint=message_endpoint, methods=["POST"]),
]

mcp_app = Starlette(routes=routes)
