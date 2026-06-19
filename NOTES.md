# NOTES

## Architecture

The service is organized into routing, services, repositories, realtime, and database layers.

- `app/main.py` builds the FastAPI app, middleware, and lifespan hooks.
- `app/api/routes/*` contains REST endpoints.
- `app/realtime/ws_routes.py` contains the WebSocket endpoint route.
- `app/realtime/manager.py` manages in-memory socket connections per conversation.
- `app/realtime/pubsub.py` manages Redis pub/sub fan-out.
- `app/services/*` contains business logic.
- `app/db/*` contains async database session management and repositories.

This keeps `main.py` thin and keeps the realtime code isolated from REST concerns. FastAPI router-based project organization is the standard approach for larger applications. 

## REST vs WebSocket split

I used:
- REST for auth, conversation CRUD, and message history
- WebSocket for live send/broadcast messaging

This matches the assignment guidance and keeps the real-time path focused only on connection-oriented messaging.

## WebSocket authentication choice

I authenticate the WebSocket using the JWT access token passed in the query string:
`/ws/conversations/{conversation_id}?token=<access_token>`

Why this choice:
- easy to test with browser tools, Postman, and websocat
- auth happens during connect time
- simpler to demonstrate in a take-home assignment

Trade-off:
- query params are less ideal than header/subprotocol-based transport in some production environments, so in a production system I would likely prefer a header or an auth-frame depending on the client platform. The assignment explicitly allows query param, subprotocol, or first-message auth as long as the choice is justified.

## Message protocol

The socket uses structured JSON messages.

Client -> server:

```json
{
  "content": "Hello"
}
```

Server -> client event example:

```json
{
  "type": "message.created",
  "message": {
    "id": "uuid",
    "conversation_id": "uuid",
    "role": "user",
    "content": "Hello",
    "created_at": "2026-06-19T08:00:00Z"
  }
}
```

Error example:

```json
{
  "type": "error",
  "code": "assistant_error",
  "message": "Assistant reply failed: ...",
  "timestamp": "2026-06-19T08:00:01Z"
}
```

This gives a stable envelope for clients and aligns with the assignment’s request for a clear JSON protocol with types, ids, and errors.

## Redis fan-out design

Each app instance:
1. accepts local WebSocket connections and stores them in memory by conversation id
2. publishes chat events to a shared Redis channel
3. subscribes to that same Redis channel on startup
4. rebroadcasts incoming Redis events to local sockets connected to that instance

This is necessary because in-memory broadcasting only reaches clients connected to one process, while Redis pub/sub allows other app instances to receive and rebroadcast the same event. The assignment explicitly requires this to work across 2+ instances.

## Persistence flow

When a user sends a message:
1. validate socket auth and conversation access
2. persist user message to PostgreSQL
3. broadcast user message
4. generate mock assistant reply
5. persist assistant reply
6. broadcast assistant reply

History is fetched via REST with offset pagination.

## Error handling

- invalid or expired socket tokens are rejected with close code `1008`
- assistant generation failures are returned as socket error events and do not crash the connection
- stale sockets are cleaned up during broadcast failures
- application resources are started and stopped through FastAPI lifespan

Lifespan is used because it is the modern resource management pattern in FastAPI for startup and shutdown tasks.

## Security

- passwords are hashed
- JWT access tokens are validated before protected access
- secrets are loaded from environment variables
- WebSocket access is denied if the user is missing or does not have access to the conversation

## What I intentionally cut

Because the assignment emphasizes doing the core four required areas well within 2–3 days, I intentionally skipped:
- OAuth login
- streamed assistant tokens
- presence / typing indicators
- Redis rate limiting
- delivery guarantees / dedupe
- metrics / Prometheus
- soft delete / restore
- cursor-based pagination

The assignment explicitly encourages honest scope control and says a smaller solid service is better than a larger half-working one. 

## Self-critique

What is strong:
- core auth, persistence, WebSocket messaging, and Redis cross-instance fan-out are implemented
- the code is modular and async-first
- the system is demonstrable with 2 app instances

What I would improve with more time:
- stronger delivery semantics with client-supplied message ids
- more integration tests around cross-instance fan-out
- metrics 
- background retry/reconnect behavior for Redis subscriber recovery