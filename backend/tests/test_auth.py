def test_auth_flow(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Auth User",
            "email": "auth@example.com",
            "password": "StrongPass123",
        },
    )
    assert register.status_code == 201, register.text
    payload = register.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "auth@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200, login.text
    token_payload = login.json()
    access_token = token_payload["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "auth@example.com"

    protected = client.get(
        "/api/v1/auth/protected",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert protected.status_code == 200, protected.text

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": payload["refresh_token"]},
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]
