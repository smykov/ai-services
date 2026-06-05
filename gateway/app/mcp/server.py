import json
import asyncio
import uuid

from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route

from .tools import TOOL_DEFINITIONS, handle_tool_call


async def sse_endpoint(request):
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
    body = await request.json()
    method = body.get("method")
    msg_id = body.get("id")

    if method == "initialize":
        return _json_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "0.1.0",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "ecosystem-ai-services",
                    "version": "0.1.0",
                },
            },
        })

    if method == "tools/list":
        return _json_response({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOL_DEFINITIONS},
        })

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            result = await handle_tool_call(name, arguments)
            return _json_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
            })
        except Exception as e:
            return _json_response({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(e)},
            })

    return _json_response({
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    })


def _json_response(data: dict, status: int = 200):
    from starlette.responses import JSONResponse
    return JSONResponse(data, status_code=status)


routes = [
    Route("/mcp", endpoint=sse_endpoint, methods=["GET"]),
    Route("/mcp", endpoint=message_endpoint, methods=["POST"]),
]

mcp_app = Starlette(routes=routes)
