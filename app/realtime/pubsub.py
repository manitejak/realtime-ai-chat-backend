import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis

logger = logging.getLogger(__name__)
BroadcastHandler = Callable[[str, dict], Awaitable[None]]


class RedisPubSub:
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30,
        )
        self.pubsub = self.redis.pubsub()
        self.task: asyncio.Task | None = None
        self.channel = "chat_messages"
        self.instance_id = str(uuid.uuid4())

    async def start(self, handler: BroadcastHandler) -> None:
        await self.pubsub.subscribe(self.channel)
        logger.info(
            "redis_pubsub_started channel=%s instance_id=%s",
            self.channel,
            self.instance_id,
        )
        self.task = asyncio.create_task(
            self._reader(handler),
            name=f"redis-reader-{self.instance_id}",
        )
        self.task.add_done_callback(self._on_reader_done)

    def _on_reader_done(self, task: asyncio.Task) -> None:
        try:
            exc = task.exception()
            if exc:
                logger.exception(
                    "redis_pubsub_task_failed instance_id=%s",
                    self.instance_id,
                    exc_info=exc,
                )
            else:
                logger.warning(
                    "redis_pubsub_task_stopped instance_id=%s",
                    self.instance_id,
                )
        except asyncio.CancelledError:
            logger.info(
                "redis_pubsub_task_cancelled instance_id=%s",
                self.instance_id,
            )

    async def _reader(self, handler: BroadcastHandler) -> None:
        logger.info("redis_pubsub_reader_running instance_id=%s", self.instance_id)

        while True:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    await asyncio.sleep(0.05)
                    continue

                logger.info(
                    "redis_raw_message instance_id=%s message=%s",
                    self.instance_id,
                    message,
                )

                data = json.loads(message["data"])
                conversation_id = data["conversation_id"]
                payload = data["payload"]
                origin_instance_id = data.get("origin_instance_id")

                logger.info(
                    "redis_message_received conversation_id=%s origin_instance_id=%s instance_id=%s",
                    conversation_id,
                    origin_instance_id,
                    self.instance_id,
                )

                if origin_instance_id == self.instance_id:
                    logger.info(
                        "redis_message_skipped_same_origin conversation_id=%s instance_id=%s",
                        conversation_id,
                        self.instance_id,
                    )
                    continue

                await handler(conversation_id, payload)

            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "redis_pubsub_reader_failed instance_id=%s",
                    self.instance_id,
                )
                await asyncio.sleep(1)

    async def publish(self, conversation_id: str, payload: dict) -> None:
        message = {
            "conversation_id": conversation_id,
            "payload": payload,
            "origin_instance_id": self.instance_id,
        }
        await self.redis.publish(self.channel, json.dumps(message))
        logger.info(
            "redis_message_published conversation_id=%s instance_id=%s",
            conversation_id,
            self.instance_id,
        )

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

        await self.pubsub.unsubscribe(self.channel)
        await self.pubsub.aclose()
        await self.redis.aclose()