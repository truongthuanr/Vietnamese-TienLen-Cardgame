from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from .room_service import create_room, join_room, leave_room
from .ws_service import websocket_endpoint


async def homepage(request):
    return JSONResponse({"status": "ok"})




routes = [
    Route("/", homepage),
    Route("/rooms", create_room, methods=["POST"]),
    Route("/rooms/{code:str}/join", join_room, methods=["POST"]),
    Route("/rooms/{code:str}/leave", leave_room, methods=["POST"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

app = Starlette(routes=routes)
