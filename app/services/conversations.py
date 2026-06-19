from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.messages import MessageRepository


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversations = ConversationRepository(session)
        self.messages = MessageRepository(session)

    async def create(self, user_id: str, title: str):
        conversation = await self.conversations.create(user_id, title)
        await self.session.commit()
        return conversation

    async def list(self, user_id: str):
        return await self.conversations.list_for_user(user_id)

    async def update(self, user_id: str, conversation_id: str, title: str):
        conversation = await self.conversations.get_for_user(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')
        conversation.title = title
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def delete(self, user_id: str, conversation_id: str) -> None:
        conversation = await self.conversations.get_for_user(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')
        await self.conversations.delete(conversation)
        await self.session.commit()

    async def history(self, user_id: str, conversation_id: str, limit: int, offset: int):
        conversation = await self.conversations.get_for_user(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')
        return await self.messages.list_for_conversation(conversation_id, limit, offset)

    async def ensure_access(self, user_id: str, conversation_id: str):
        conversation = await self.conversations.get_for_user(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found')
        return conversation