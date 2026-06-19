def test_create_and_list_conversations(client, auth_headers):
    create_resp = client.post(
        "/api/v1/conversations",
        headers=auth_headers,
        json={"title": "Project Chat"},
    )
    assert create_resp.status_code in (200, 201)

    list_resp = client.get("/api/v1/conversations", headers=auth_headers)
    assert list_resp.status_code == 200

    items = list_resp.json()
    assert isinstance(items, list)
    assert any(item["title"] == "Project Chat" for item in items)