from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from .room_service import create_room, join_room, leave_room


async def homepage(request):
    return JSONResponse({"status": "ok"})


async def websocket_endpoint(websocket):
    await websocket.accept()
    await websocket.send_json({"event": "connected"})
    await websocket.close()


routes = [
    Route("/", homepage),
    Route("/rooms", create_room, methods=["POST"]),
    Route("/rooms/{code:str}/join", join_room, methods=["POST"]),
    Route("/rooms/{code:str}/leave", leave_room, methods=["POST"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

app = Starlette(routes=routes)
