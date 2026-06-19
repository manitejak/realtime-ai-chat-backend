from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.schemas.conversations import ConversationCreateRequest, ConversationResponse, ConversationUpdateRequest, MessageResponse
from app.services.conversations import ConversationService

router = APIRouter(prefix='/conversations', tags=['conversations'])


@router.post('', response_model=ConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreateRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> ConversationResponse:
    conversation = await ConversationService(session).create(current_user.id, payload.title)
    return ConversationResponse.model_validate(conversation, from_attributes=True)


@router.get('', response_model=list[ConversationResponse])
async def list_conversations(current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> list[ConversationResponse]:
    conversations = await ConversationService(session).list(current_user.id)
    return [ConversationResponse.model_validate(item, from_attributes=True) for item in conversations]


@router.patch('/{conversation_id}', response_model=ConversationResponse)
async def rename_conversation(conversation_id: str, payload: ConversationUpdateRequest, current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> ConversationResponse:
    conversation = await ConversationService(session).update(current_user.id, conversation_id, payload.title)
    return ConversationResponse.model_validate(conversation, from_attributes=True)


@router.delete('/{conversation_id}', status_code=204)
async def delete_conversation(conversation_id: str, current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> Response:
    await ConversationService(session).delete(current_user.id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/{conversation_id}/messages', response_model=list[MessageResponse])
async def get_history(conversation_id: str, limit: int = 50, offset: int = 0, current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db_session)) -> list[MessageResponse]:
    messages = await ConversationService(session).history(current_user.id, conversation_id, limit=min(limit, 100), offset=max(offset, 0))
    return [MessageResponse.model_validate(item, from_attributes=True) for item in messages]