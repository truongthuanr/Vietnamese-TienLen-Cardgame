import logging
import time
from uuid import uuid4

from starlette.applications import Starlette
from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from logging_config import configure_logging
from room_service import create_room, join_room, leave_room
from swagger import openapi, swagger_ui
from user_service import create_user, get_user_handler
from ws_service import websocket_endpoint

configure_logging()
logger = logging.getLogger("tienlen.app")


async def homepage(request):
    """
    ---
    summary: Health check
    responses:
      200:
        description: OK
    """
    return JSONResponse({"status": "ok"})

routes = [
    Route("/", homepage),
    Route("/openapi.json", openapi),
    Route("/docs", swagger_ui),
    Route("/users", create_user, methods=["POST"]),
    Route("/users/{user_id:str}", get_user_handler, methods=["GET"]),
    Route("/rooms", create_room, methods=["POST"]),
    Route("/rooms/{code:str}/join", join_room, methods=["POST"]),
    Route("/rooms/{code:str}/leave", leave_room, methods=["POST"]),
    WebSocketRoute("/ws", websocket_endpoint),
]

app = Starlette(routes=routes)


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code if response else 500
        client = request.client.host if request.client else "-"
        logger.info(
            "request request_id=%s client=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            client,
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )
        if response is not None:
            MutableHeaders(response.headers)["x-request-id"] = request_id


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "unhandled_exception request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        {"error": "Internal server error", "request_id": request_id},
        status_code=500,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
