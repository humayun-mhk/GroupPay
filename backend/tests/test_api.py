from tests.conftest import auth, register


def test_register_login_invalid_login_and_me(client):
    created = register(client, "Humayun Ahmed", "humayun@example.com")
    assert created["access_token"] and created["refresh_token"]
    assert "password_hash" not in created["user"]
    assert client.get("/api/v1/auth/me", headers=auth(created["access_token"])).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"email": "humayun@example.com", "password": "Password123!"}
    )
    assert login.status_code == 200
    invalid = client.post(
        "/api/v1/auth/login", json={"email": "humayun@example.com", "password": "wrong"}
    )
    assert invalid.status_code == 401


def test_invalid_password_login(client):
    register(client, "Ali Khan", "ali@example.com")
    response = client.post(
        "/api/v1/auth/login", json={"email": "ali@example.com", "password": "incorrect-password"}
    )
    assert response.status_code == 401


def test_friend_request_duplicate_accept_and_list(client):
    humayun = register(client, "Humayun Ahmed", "humayun@example.com")
    ali = register(client, "Ali Khan", "ali@example.com")
    headers = auth(humayun["access_token"])
    request = client.post("/api/v1/friends/requests/2", headers=headers)
    assert request.status_code == 201
    assert client.post("/api/v1/friends/requests/2", headers=headers).status_code == 409
    incoming = client.get("/api/v1/friends/requests/incoming", headers=auth(ali["access_token"]))
    assert incoming.status_code == 200 and len(incoming.json()) == 1
    accepted = client.post(
        f"/api/v1/friends/requests/{request.json()['id']}/accept", headers=auth(ali["access_token"])
    )
    assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"
    friends = client.get("/api/v1/friends", headers=headers)
    assert friends.status_code == 200 and friends.json()[0]["user"]["id"] == 2


def test_group_creator_admin_and_admin_adds_accepted_friend(client):
    humayun = register(client, "Humayun Ahmed", "humayun@example.com")
    ali = register(client, "Ali Khan", "ali@example.com")
    headers = auth(humayun["access_token"])
    friend_request = client.post("/api/v1/friends/requests/2", headers=headers).json()
    client.post(
        f"/api/v1/friends/requests/{friend_request['id']}/accept", headers=auth(ali["access_token"])
    )
    created = client.post("/api/v1/groups", headers=headers, json={"name": "Trip"})
    assert created.status_code == 201 and created.json()["current_user_role"] == "ADMIN"
    group_id = created.json()["id"]
    added = client.post(f"/api/v1/groups/{group_id}/members", headers=headers, json={"user_id": 2})
    assert added.status_code == 201 and added.json()["role"] == "MEMBER"
    detail = client.get(f"/api/v1/groups/{group_id}", headers=headers)
    assert detail.status_code == 200 and detail.json()["members_count"] == 2


def test_normal_member_cannot_add_member(client):
    owner = register(client, "Group Owner", "owner@example.com")
    member = register(client, "Group Member", "member@example.com")
    guest = register(client, "Another Friend", "guest@example.com")
    owner_headers, member_headers = auth(owner["access_token"]), auth(member["access_token"])
    req = client.post("/api/v1/friends/requests/2", headers=owner_headers).json()
    client.post(
        f"/api/v1/friends/requests/{req['id']}/accept", headers=auth(member["access_token"])
    )
    req = client.post("/api/v1/friends/requests/3", headers=member_headers).json()
    client.post(f"/api/v1/friends/requests/{req['id']}/accept", headers=auth(guest["access_token"]))
    group = client.post("/api/v1/groups", headers=owner_headers, json={"name": "Dinner"}).json()
    client.post(f"/api/v1/groups/{group['id']}/members", headers=owner_headers, json={"user_id": 2})
    response = client.post(
        f"/api/v1/groups/{group['id']}/members", headers=member_headers, json={"user_id": 3}
    )
    assert response.status_code == 403


def test_group_visibility_and_last_admin_protection(client):
    owner = register(client, "Owner Person", "owner@example.com")
    other = register(client, "Outside Person", "outside@example.com")
    group = client.post(
        "/api/v1/groups", headers=auth(owner["access_token"]), json={"name": "Private group"}
    ).json()
    hidden = client.get(f"/api/v1/groups/{group['id']}", headers=auth(other["access_token"]))
    assert hidden.status_code == 404
    last_admin = client.delete(
        f"/api/v1/groups/{group['id']}/members/1", headers=auth(owner["access_token"])
    )
    assert last_admin.status_code == 400
