from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, owner_id: str, title: str) -> Conversation:
        conversation = Conversation(owner_id=owner_id, title=title)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def list_for_user(self, owner_id: str) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(Conversation.owner_id == owner_id).order_by(desc(Conversation.updated_at))
        )
        return list(result.scalars().all())

    async def get_for_user(self, conversation_id: str, owner_id: str) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, conversation: Conversation) -> None:
        await self.session.delete(conversation)
        await self.session.flush()