from tests.conftest import auth_header


def test_register_success(client):
    resp = client.post(
        "/register",
        json={"email": "a@b.com", "password": "pass", "full_name": "A"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "a@b.com"
    assert "id" in data
    assert "password" not in data


def test_register_duplicate_email(client, registered_user):
    resp = client.post(
        "/register",
        json={
            "email": registered_user["email"],
            "password": "other",
        },
    )
    assert resp.status_code == 400


def test_login_success(client, registered_user):
    resp = client.post(
        "/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client, registered_user):
    resp = client.post(
        "/login",
        data={"username": registered_user["email"], "password": "wrong"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_without_token(client):
    resp = client.get("/users")
    assert resp.status_code == 401


def test_list_users(client, auth_token):
    resp = client.get("/users", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_get_current_user(client, auth_token):
    resp = client.get("/users/me", headers=auth_header(auth_token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_invalid_token(client):
    resp = client.get("/users", headers=auth_header("garbage.token.here"))
    assert resp.status_code == 401
