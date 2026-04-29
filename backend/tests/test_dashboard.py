def _create_attempt(client, headers, payload):
    response = client.post("/api/v1/biometric/check-in", headers=headers, json=payload)
    assert response.status_code == 201, response.text


def test_dashboard_endpoints(client, auth_headers):
    _create_attempt(client, auth_headers, {"spoken_phrase": "I authorize this access."})
    _create_attempt(
        client,
        auth_headers,
        {
            "spoken_phrase": "almost right phrase",
            "expected_phrase": "I authorize this access.",
            "face_capture_quality": 0.78,
            "voice_capture_quality": 0.76,
            "liveness_hint": 0.83,
        },
    )

    summary = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["total_attempts"] == 2

    recent = client.get("/api/v1/dashboard/recent-attempts", headers=auth_headers)
    assert recent.status_code == 200, recent.text
    assert len(recent.json()["items"]) == 2

    risk_distribution = client.get("/api/v1/dashboard/risk-distribution", headers=auth_headers)
    assert risk_distribution.status_code == 200, risk_distribution.text
    assert risk_distribution.json()["items"]

    trend = client.get("/api/v1/dashboard/confidence-trend?days=7", headers=auth_headers)
    assert trend.status_code == 200, trend.text
    assert len(trend.json()["items"]) == 7
