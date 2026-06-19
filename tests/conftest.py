import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def unique_email():
    return f"test-{uuid.uuid4().hex}@example.com"


@pytest.fixture(scope="session")
def auth_tokens(client, unique_email):
    signup_payload = {
        "email": unique_email,
        "password": "StrongPass123!"
    }

    signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)

    # Accept duplicate-user state if DB was not clean, but only if login still works.
    assert signup_resp.status_code in (200, 201, 409), signup_resp.text

    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "StrongPass123!"
        },
    )
    assert login_resp.status_code == 200, login_resp.text

    body = login_resp.json()
    assert "access_token" in body, body
    return body


@pytest.fixture(scope="session")
def access_token(auth_tokens):
    return auth_tokens["access_token"]


@pytest.fixture(scope="session")
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def conversation_id(client, auth_headers):
    resp = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Test Conversation"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["id"]