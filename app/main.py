import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.realtime.manager import ConnectionManager
from app.realtime.pubsub import RedisPubSub
from app.realtime.ws_routes import router as ws_router, set_runtime_dependencies

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

manager = ConnectionManager()
pubsub = RedisPubSub(settings.redis_url)


async def send_json(websocket: WebSocket, payload: dict) -> None:
    await websocket.send_json(payload)


async def fanout_handler(conversation_id: str, payload: dict) -> None:
    logger.info("fanout_handler_called conversation_id=%s payload=%s", conversation_id, payload)
    await manager.broadcast_local(conversation_id, payload, send_json)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pubsub.start(fanout_handler)
    try:
        yield
    finally:
        await manager.close_all()
        await pubsub.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

set_runtime_dependencies(manager=manager, pubsub=pubsub)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(ws_router)