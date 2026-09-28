
import pytest

from tests.support.factories import DEFAULT_PASSWORD

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


class TestRegister:
    async def test_register_returns_token_and_user(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "supersecret1"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"]
        assert body["user"]["username"] == "newuser"
        assert body["user"]["email"] == "newuser@example.com"

    async def test_register_seeds_default_categories(self, unauthenticated_client, db):
        resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "supersecret1"},
        )
        user_id = resp.json()["user"]["id"]

        categories = await db.categories.find({"user_id": user_id}).to_list(length=100)

        assert len(categories) > 0
        assert all(c["is_default"] for c in categories)

    async def test_duplicate_email_is_rejected(self, unauthenticated_client):
        payload = {"username": "user1", "email": "dup@example.com", "password": "supersecret1"}
        await unauthenticated_client.post("/api/auth/register", json=payload)

        resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "user2", "email": "dup@example.com", "password": "othersecret1"},
        )

        assert resp.status_code == 400

    async def test_duplicate_username_is_rejected(self, unauthenticated_client):
        await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "dupname", "email": "a@example.com", "password": "supersecret1"},
        )

        resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "dupname", "email": "b@example.com", "password": "othersecret1"},
        )

        assert resp.status_code == 400

    async def test_invalid_email_is_rejected(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "user1", "email": "not-an-email", "password": "supersecret1"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_with_correct_credentials_returns_token(self, unauthenticated_client):
        await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "loginuser", "email": "login@example.com", "password": "correctpassword"},
        )

        resp = await unauthenticated_client.post(
            "/api/auth/login",
            json={"username": "", "email": "login@example.com", "password": "correctpassword"},
        )

        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_login_with_wrong_password_returns_401(self, unauthenticated_client):
        await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "loginuser", "email": "login@example.com", "password": "correctpassword"},
        )

        resp = await unauthenticated_client.post(
            "/api/auth/login",
            json={"username": "", "email": "login@example.com", "password": "wrongpassword"},
        )

        assert resp.status_code == 401

    async def test_login_with_unknown_email_returns_401(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/auth/login",
            json={"username": "", "email": "nobody@example.com", "password": "whatever123"},
        )
        assert resp.status_code == 401

    async def test_login_without_username_field_returns_422(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
        )
        assert resp.status_code == 422


class TestMe:
    async def test_me_returns_current_user_with_valid_token(self, unauthenticated_client):
        register_resp = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "meuser", "email": "me@example.com", "password": "supersecret1"},
        )
        token = register_resp.json()["access_token"]

        resp = await unauthenticated_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    async def test_me_without_token_returns_401(self, unauthenticated_client):
        resp = await unauthenticated_client.get("/api/auth/me")
        assert resp.status_code == 401


async def login(client, email: str, password: str):
    return await client.post("/api/auth/login", json={"email": email, "password": password, "username": ""})


class TestUpdateProfile:
    async def test_changes_username_and_email(self, make, jwt_client, db):
        user = await make.user()

        resp = await jwt_client(user).put("/api/auth/me", json={"username": "renamed", "email": "new@example.com"})

        assert resp.status_code == 200
        assert resp.json()["username"] == "renamed"
        assert resp.json()["email"] == "new@example.com"
        stored = await db.users.find_one({"_id": user["_id"]})
        assert (stored["username"], stored["email"]) == ("renamed", "new@example.com")

    async def test_partial_update_keeps_the_other_fields(self, make, jwt_client):
        user = await make.user()
        body = (await jwt_client(user).put("/api/auth/me", json={"username": "only-name"})).json()
        assert body["username"] == "only-name"
        assert body["email"] == user["email"]

    async def test_empty_update_changes_nothing(self, make, jwt_client):
        user = await make.user()
        body = (await jwt_client(user).put("/api/auth/me", json={})).json()
        assert (body["username"], body["email"]) == (user["username"], user["email"])

    async def test_new_email_is_used_for_login(self, make, jwt_client, unauthenticated_client):
        user = await make.user()
        await jwt_client(user).put("/api/auth/me", json={"email": "moved@example.com"})

        assert (await login(unauthenticated_client, "moved@example.com", DEFAULT_PASSWORD)).status_code == 200
        assert (await login(unauthenticated_client, user["email"], DEFAULT_PASSWORD)).status_code == 401

    async def test_keeping_the_same_email_is_allowed(self, make, jwt_client):
        user = await make.user()
        resp = await jwt_client(user).put("/api/auth/me", json={"email": user["email"]})
        assert resp.status_code == 200

    async def test_invalid_email_is_rejected(self, make, jwt_client):
        user = await make.user()
        assert (await jwt_client(user).put("/api/auth/me", json={"email": "not-an-email"})).status_code == 422

    async def test_password_hash_cannot_be_set_through_the_profile(self, make, jwt_client, db):
        user = await make.user()
        await jwt_client(user).put("/api/auth/me", json={"hashed_password": "x"})
        assert (await db.users.find_one({"_id": user["_id"]}))["hashed_password"] == user["hashed_password"]

    @pytest.mark.xfail(strict=True, reason="taking another user's email crashes with a duplicate key error")
    async def test_email_of_another_user_is_rejected(self, lenient_client, other_user):
        resp = await lenient_client.put("/api/auth/me", json={"email": other_user["email"]})
        assert resp.status_code in (400, 409)

    @pytest.mark.xfail(strict=True, reason="taking another user's username crashes with a duplicate key error")
    async def test_username_of_another_user_is_rejected(self, lenient_client, other_user):
        resp = await lenient_client.put("/api/auth/me", json={"username": other_user["username"]})
        assert resp.status_code in (400, 409)

    async def test_requires_authentication(self, unauthenticated_client):
        assert (await unauthenticated_client.put("/api/auth/me", json={"username": "x"})).status_code == 401


class TestChangePassword:
    async def test_new_password_works_and_old_one_stops_working(self, make, jwt_client, unauthenticated_client):
        user = await make.user()

        resp = await jwt_client(user).post(
            "/api/auth/change-password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": "brand-new-pw-1"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"message": "Password updated successfully"}
        assert (await login(unauthenticated_client, user["email"], "brand-new-pw-1")).status_code == 200
        assert (await login(unauthenticated_client, user["email"], DEFAULT_PASSWORD)).status_code == 401

    async def test_wrong_current_password_is_rejected_and_nothing_changes(self, make, jwt_client, db):
        user = await make.user()

        resp = await jwt_client(user).post(
            "/api/auth/change-password", json={"current_password": "wrong", "new_password": "whatever-1"}
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Current password is incorrect"
        assert (await db.users.find_one({"_id": user["_id"]}))["hashed_password"] == user["hashed_password"]

    @pytest.mark.parametrize("missing", ["current_password", "new_password"])
    async def test_missing_field_is_rejected(self, make, jwt_client, missing):
        user = await make.user()
        payload = {"current_password": DEFAULT_PASSWORD, "new_password": "whatever-1"}
        del payload[missing]
        assert (await jwt_client(user).post("/api/auth/change-password", json=payload)).status_code == 422

    @pytest.mark.xfail(strict=True, reason="an empty new password is accepted")
    async def test_empty_new_password_is_rejected(self, make, jwt_client):
        user = await make.user()
        resp = await jwt_client(user).post(
            "/api/auth/change-password", json={"current_password": DEFAULT_PASSWORD, "new_password": ""}
        )
        assert resp.status_code == 422

    async def test_requires_authentication(self, unauthenticated_client):
        resp = await unauthenticated_client.post(
            "/api/auth/change-password", json={"current_password": "a", "new_password": "b"}
        )
        assert resp.status_code == 401
