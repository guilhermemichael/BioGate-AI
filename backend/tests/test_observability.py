def test_health_ready_and_metrics(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert "database" in ready.json()["checks"]

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "biogate_http_requests_total" in metrics.text
