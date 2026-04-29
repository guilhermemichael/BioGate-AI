def test_refresh_rotation_logout_and_devices(client):
    register = client.post(
        "/api/v1/auth/register",
        headers={"x-device-fingerprint": "browser=en-US|platform=win32|screen=1920x1080"},
        json={
            "full_name": "Owner One",
            "email": "owner1@example.com",
            "password": "StrongPass123",
            "organization_name": "Owner One Org",
        },
    )
    assert register.status_code == 201, register.text
    payload = register.json()
    access_token = payload["access_token"]
    refresh_token = payload["refresh_token"]

    devices = client.get("/api/v1/auth/devices", headers={"Authorization": f"Bearer {access_token}"})
    assert devices.status_code == 200, devices.text
    assert len(devices.json()["items"]) == 1
    assert devices.json()["items"][0]["is_trusted"] is True

    sessions = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access_token}"})
    assert sessions.status_code == 200, sessions.text
    assert len(sessions.json()["items"]) == 1
    session_id = sessions.json()["items"][0]["id"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    refreshed_payload = refreshed.json()
    assert refreshed_payload["refresh_token"] != refresh_token
    assert refreshed_payload["session_id"] == session_id

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed_payload['access_token']}"},
        json={"revoke_all": False},
    )
    assert logout.status_code == 200, logout.text
    assert logout.json()["revoked_count"] == 1

    after_logout = client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {refreshed_payload['access_token']}"},
    )
    assert after_logout.status_code == 401, after_logout.text


def test_tenant_isolation_and_viewer_permissions(client):
    owner_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner One",
            "email": "owner-one@example.com",
            "password": "StrongPass123",
            "organization_name": "Tenant Alpha",
        },
    )
    assert owner_one.status_code == 201, owner_one.text
    owner_one_payload = owner_one.json()
    owner_one_headers = {"Authorization": f"Bearer {owner_one_payload['access_token']}"}

    attempt = client.post(
        "/api/v1/biometric/check-in",
        headers=owner_one_headers,
        json={"spoken_phrase": "I authorize this access."},
    )
    assert attempt.status_code == 201, attempt.text
    attempt_id = attempt.json()["attempt_id"]
    organization_slug = owner_one_payload["user"]["organization"]["slug"]

    viewer = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Viewer User",
            "email": "viewer@example.com",
            "password": "StrongPass123",
            "organization_slug": organization_slug,
        },
    )
    assert viewer.status_code == 201, viewer.text
    viewer_headers = {"Authorization": f"Bearer {viewer.json()['access_token']}"}
    assert viewer.json()["user"]["role"] == "viewer"

    viewer_dashboard = client.get("/api/v1/dashboard/summary", headers=viewer_headers)
    assert viewer_dashboard.status_code == 200, viewer_dashboard.text

    viewer_logs = client.get("/api/v1/logs", headers=viewer_headers)
    assert viewer_logs.status_code == 403, viewer_logs.text

    viewer_checkin = client.post(
        "/api/v1/biometric/check-in",
        headers=viewer_headers,
        json={"spoken_phrase": "I authorize this access."},
    )
    assert viewer_checkin.status_code == 403, viewer_checkin.text

    owner_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Two",
            "email": "owner-two@example.com",
            "password": "StrongPass123",
            "organization_name": "Tenant Beta",
        },
    )
    assert owner_two.status_code == 201, owner_two.text
    owner_two_headers = {"Authorization": f"Bearer {owner_two.json()['access_token']}"}

    tenant_isolation = client.get(f"/api/v1/biometric/attempts/{attempt_id}", headers=owner_two_headers)
    assert tenant_isolation.status_code == 404, tenant_isolation.text


def test_login_rate_limit_triggers_429(client):
    for index in range(12):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "StrongPass123"},
        )
        assert response.status_code == 401, f"request {index} should still be unauthorized"

    throttled = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "StrongPass123"},
    )
    assert throttled.status_code == 429, throttled.text
