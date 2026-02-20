from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute


async def homepage(request):
    return JSONResponse({"status": "ok"})


async def websocket_endpoint(websocket):
    await websocket.accept()
    await websocket.send_json({"event": "connected"})
    await websocket.close()


routes = [
    Route("/", homepage),
    WebSocketRoute("/ws", websocket_endpoint),
]

app = Starlette(routes=routes)
