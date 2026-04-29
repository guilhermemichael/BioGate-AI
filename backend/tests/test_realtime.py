def test_realtime_websocket_checkin(client, registered_user):
    token = registered_user["access_token"]
    with client.websocket_connect(f"/ws/biometric/check-in/demo-session?token={token}") as websocket:
        websocket.send_json({"spoken_phrase": "I authorize this access."})
        events = []
        for _ in range(8):
            events.append(websocket.receive_json())

    assert events[0]["event"] == "CHECKIN_STARTED"
    assert events[-1]["event"] == "DECISION_READY"
    assert events[-1]["result"]["status"] in {"approved", "manual_review", "denied"}
