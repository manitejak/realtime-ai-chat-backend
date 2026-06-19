# Real-Time AI Chat Backend

A small real-time chat backend built with FastAPI, PostgreSQL, Redis pub/sub, WebSockets, and async SQLAlchemy.

## Overview

This service supports authenticated users creating conversations, fetching message history, and exchanging messages with a mock AI assistant over WebSockets. Messages are persisted in PostgreSQL and fanned out across app instances through Redis pub/sub.

## Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy async / asyncpg
- Alembic
- Pydantic v2
- Docker Compose

## Implemented scope

- Email/password signup and login
- JWT access and refresh tokens
- WebSocket authentication using access token in query param
- Conversation create, list, rename, delete
- Real-time user message broadcast
- Mock assistant reply broadcast
- Redis pub/sub fan-out across 2+ app instances
- Structured logging
- Graceful startup and shutdown via lifespan

## Not implemented

Intentionally skipped due to time and scope:
- OAuth login
- Typing indicators / presence
- Streamed token-by-token assistant response
- Per-user Redis rate limiting
- Delivery guarantees / dedupe
- Metrics / Prometheus
- Soft delete / restore
- Cursor-based pagination

## Project structure

```text
app/
  api/
    routes/
      auth.py
      conversations.py
      health.py
  core/
  db/
  realtime/
    manager.py
    pubsub.py
    ws_routes.py
  schemas/
  services/
  main.py
alembic/
tests/
docker-compose.yml
README.md
NOTES.md
.env.example
requirements.txt
```

## Environment

Create a `.env` file. or copy from .env.example 

```env
APP_NAME=Real-Time AI Chat Backend
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
DATABASE_URL=postgresql+asyncpg://chat:chat@postgres:5432/chatdb
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY='5de789009c90a062204c548ede7e611901e4395c256ac5030c9f9e0eb33866fc' -can be generated online (https://jwtsecrets.com/)
JWT_REFRESH_SECRET_KEY='5546a0fc14577bc4f1a2e21f3999fd463216ee8f756fbfe481a0c6b8da09d472' - have to generate it twice 
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
BCRYPT_ROUNDS=12
```

If running the app outside Docker, adjust DB and Redis host values accordingly.

## Run with Docker

```bash
docker compose up --build
```

If migrations are not auto-run in your setup, run:

```bash
docker compose exec api alembic upgrade head
```

## Run locally

Install dependencies and start infrastructure first.

```bash
pip install -r requirements.txt
docker compose up postgres redis -d

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

To verify Redis cross-instance fan-out, run a second instance:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## API flow

swagger - http://localhost:8000/docs
swagger docs -http://localhost:8000/redoc

### 1. Sign up

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPass123!"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPass123!"
  }'
```

Copy the `access_token`.

### 3. Create a conversation

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test conversation"
  }'
```

Copy the `conversation_id`.

### 4. Fetch history

```bash
curl "http://localhost:8000/api/v1/conversations/<CONVERSATION_ID>/messages?limit=20&offset=0" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### 5. Open WebSocket - can be tested in postman

Connect to:

```text
ws://localhost:8000/ws/conversations/<CONVERSATION_ID>?token=<ACCESS_TOKEN>
```

Example message to send:

```json
{
  "content": "Hello"
}
```

Expected socket events:
- user message event
- assistant message event

## Manual demo scenarios

### Same-instance broadcast
1. Open two tabs/clients on port `8000` with the same conversation id.
2. Send a message from tab A.
3. Verify both tabs receive the user event and assistant event.

### Cross-instance Redis fan-out
1. Start app on `8000` and `8001`.
2. Open one socket client to `8000` and one to `8001`, both for the same conversation.
3. Send a message from the `8000` client.
4. Verify the `8001` client receives the same user and assistant events through Redis fan-out.

### Reconnect + history
1. Send a few messages.
2. Disconnect the socket.
3. Reconnect or call the history endpoint.
4. Verify persisted history is returned from PostgreSQL.

## Tests

Run tests with:

```bash
docker compose exec api python -m pytest -q
```

Suggested checks:
- auth token flow
- conversation CRUD
- websocket message protocol
- broadcast logic
- history persistence

## Design notes

- REST is used for auth, conversation CRUD, and message history.
- WebSocket is used for live messaging.
- Redis pub/sub is used to fan out events across multiple app instances, which is required because in-process broadcast does not work once the app is horizontally scaled.

## Known limitations

- Query-param WebSocket auth is used for simplicity and easy testing; this is documented in `NOTES.md`.
- Mock AI is intentionally simple because the assignment evaluates backend design, not AI 