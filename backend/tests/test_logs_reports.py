def _make_attempt(client, headers, payload):
    response = client.post("/api/v1/biometric/check-in", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_logs_and_reports(client, auth_headers):
    approved = _make_attempt(client, auth_headers, {"spoken_phrase": "I authorize this access."})
    _make_attempt(
        client,
        auth_headers,
        {
            "spoken_phrase": "wrong phrase",
            "expected_phrase": "I authorize this access.",
            "face_capture_quality": 0.55,
            "voice_capture_quality": 0.5,
            "liveness_hint": 0.5,
            "device_trusted": False,
        },
    )

    logs = client.get("/api/v1/logs?status=approved", headers=auth_headers)
    assert logs.status_code == 200, logs.text
    assert logs.json()["items"][0]["attempt_id"] == approved["attempt_id"]

    detail = client.get(f"/api/v1/logs/{approved['attempt_id']}", headers=auth_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["attempt"]["attempt_id"] == approved["attempt_id"]

    csv_report = client.get("/api/v1/reports/attempts.csv", headers=auth_headers)
    assert csv_report.status_code == 200, csv_report.text
    assert "text/csv" in csv_report.headers["content-type"]
    assert "attempt_id" in csv_report.text

    pdf_report = client.get("/api/v1/reports/security-report.pdf", headers=auth_headers)
    assert pdf_report.status_code == 200, pdf_report.text
    assert pdf_report.headers["content-type"] == "application/pdf"
    assert pdf_report.content.startswith(b"%PDF")
