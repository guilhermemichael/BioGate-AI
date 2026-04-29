def test_biometric_checkin_and_attempt_history(client, auth_headers):
    checkin = client.post(
        "/api/v1/biometric/check-in",
        headers=auth_headers,
        json={"spoken_phrase": "I authorize this access."},
    )
    assert checkin.status_code == 201, checkin.text
    payload = checkin.json()
    assert payload["status"] == "approved"
    assert payload["risk_level"] == "low"
    assert payload["final_confidence"] >= 0.85
    assert "decision_reasons" in payload

    attempts = client.get("/api/v1/biometric/attempts", headers=auth_headers)
    assert attempts.status_code == 200, attempts.text
    listing = attempts.json()
    assert listing["total"] == 1

    detail = client.get(
        f"/api/v1/biometric/attempts/{payload['attempt_id']}",
        headers=auth_headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["attempt_id"] == payload["attempt_id"]


def test_biometric_denied_flow(client, auth_headers):
    denied = client.post(
        "/api/v1/biometric/check-in",
        headers=auth_headers,
        json={
            "spoken_phrase": "totally wrong phrase",
            "expected_phrase": "I authorize this access.",
            "face_capture_quality": 0.51,
            "voice_capture_quality": 0.49,
            "liveness_hint": 0.45,
            "device_trusted": False,
            "network_trusted": False,
            "unusual_time": True,
            "location_changed": True,
        },
    )
    assert denied.status_code == 201, denied.text
    payload = denied.json()
    assert payload["status"] == "denied"
    assert payload["recommended_action"] == "deny_and_retry"
