from app.schemas.conversations import MessageResponse


def serialize_message_event(message: MessageResponse) -> dict:
    return {'type': 'message.created', 'message': message.model_dump(mode='json')}


def serialize_error(code: str, detail: str, timestamp: str) -> dict:
    return {'type': 'error', 'code': code, 'detail': detail, 'timestamp': timestamp}