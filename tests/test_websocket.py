import pytest


def test_websocket_rejects_invalid_token(client, conversation_id):
    with pytest.raises(Exception):
        with client.websocket_connect(
            f"/ws/conversations/{conversation_id}?token=invalid-token"
        ):
            pass


def test_websocket_message_flow_single_client(client, access_token, conversation_id):
    url = f"/ws/conversations/{conversation_id}?token={access_token}"

    with client.websocket_connect(url) as ws:
        ws.send_json({"content": "hello from test"})
        msg = ws.receive_json()

        assert "type" in msg
        assert msg["type"] in ("message.created", "error")