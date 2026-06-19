from sqlalchemy import asc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, conversation_id: str, sender_id: str | None, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation_id, sender_id=sender_id, role=role, content=content)
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_for_conversation(self, conversation_id: str, limit: int, offset: int) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(asc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())