from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from .room_service import create_room, join_room, leave_room
from .user_service import create_user, get_user_handler
from .ws_service import websocket_endpoint


async def homepage(request):
    return JSONResponse({"status": "ok"})




routes = [
    Route("/", homepage),
    Route("/users", create_user, methods=["POST"]),
    Route("/users/{user_id:str}", get_user_handler, methods=["GET"]),
    Route("/rooms", create_room, methods=["POST"]),
    Route("/rooms/{code:str}/join", join_room, methods=["POST"]),
    Route("/rooms/{code:str}/leave", leave_room, methods=["POST"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

app = Starlette(routes=routes)
