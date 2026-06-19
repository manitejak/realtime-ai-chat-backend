from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.messages import MessageRepository
from app.schemas.conversations import MessageResponse
from app.services.mock_ai import MockAIService


class RealtimeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messages = MessageRepository(session)
        self.ai = MockAIService()

    async def create_user_message(self, conversation_id: str, sender_id: str, content: str) -> MessageResponse:
        message = await self.messages.create(conversation_id, sender_id, 'user', content)
        await self.session.commit()
        await self.session.refresh(message)
        return MessageResponse.model_validate(message, from_attributes=True)

    async def create_assistant_message(self, conversation_id: str, content: str) -> MessageResponse:
        message = await self.messages.create(conversation_id, None, 'assistant', content)
        await self.session.commit()
        await self.session.refresh(message)
        return MessageResponse.model_validate(message, from_attributes=True)