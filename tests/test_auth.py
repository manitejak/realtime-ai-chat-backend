import uuid


def test_login_returns_access_and_refresh_tokens(client):
    email = f"login-test-{uuid.uuid4().hex}@example.com"
    password = "StrongPass123!"

    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password},
    )
    assert signup_resp.status_code in (200, 201), signup_resp.text

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"].lower() == "bearer"