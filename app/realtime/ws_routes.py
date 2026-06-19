import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.api.deps import get_ws_token
from app.core.security import TokenError, decode_access_token
from app.db.repositories.users import UserRepository
from app.db.session import AsyncSessionLocal
from app.realtime.message_serializer import serialize_error, serialize_message_event
from app.schemas.web_socket import WSChatMessageIn
from app.services.conversations import ConversationService
from app.services.mock_ai import MockAIService
from app.services.realtime import RealtimeService

logger = logging.getLogger(__name__)
router = APIRouter()
ai_service = MockAIService()

_manager = None
_pubsub = None


def set_runtime_dependencies(manager, pubsub) -> None:
    global _manager, _pubsub
    _manager = manager
    _pubsub = pubsub


async def _send_json(websocket: WebSocket, payload: dict) -> None:
    await websocket.send_json(payload)


@router.websocket("/ws/conversations/{conversation_id}")
async def conversation_socket(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Depends(get_ws_token),
):
    try:
        payload = decode_access_token(token)
    except TokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get_by_id(payload["sub"])
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return

        try:
            await ConversationService(session).ensure_access(user.id, conversation_id)
        except Exception:
            await websocket.close(code=1008, reason="Conversation access denied")
            return

    await _manager.connect(conversation_id, websocket)

    try:
        while True:
            raw = await websocket.receive_json()
            incoming = WSChatMessageIn.model_validate(raw)

            async with AsyncSessionLocal() as session:
                realtime = RealtimeService(session)
                user_message = await realtime.create_user_message(
                    conversation_id,
                    user.id,
                    incoming.content,
                )

            user_event = serialize_message_event(user_message)
            await _manager.broadcast_local(conversation_id, user_event, _send_json)
            await _pubsub.publish(conversation_id, user_event)

            try:
                assistant_reply = await ai_service.generate_reply(incoming.content)

                async with AsyncSessionLocal() as session:
                    assistant_message = await RealtimeService(session).create_assistant_message(
                        conversation_id,
                        assistant_reply,
                    )

                assistant_event = serialize_message_event(assistant_message)
                await _manager.broadcast_local(conversation_id, assistant_event, _send_json)
                await _pubsub.publish(conversation_id, assistant_event)

            except Exception as exc:
                logger.exception(
                    "assistant_generation_failed conversation_id=%s",
                    conversation_id,
                )
                await websocket.send_json(
                    serialize_error(
                        "assistant_error",
                        f"Assistant reply failed: {exc}",
                        datetime.now(timezone.utc).isoformat(),
                    )
                )

    except WebSocketDisconnect:
        await _manager.disconnect(conversation_id, websocket)

    except Exception as exc:
        logger.exception("websocket_failure conversation_id=%s", conversation_id)
        await websocket.send_json(
            serialize_error(
                "socket_error",
                str(exc),
                datetime.now(timezone.utc).isoformat(),
            )
        )
        await _manager.disconnect(conversation_id, websocket)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)