
from datetime import datetime

import pytest

from tests.support.factories import DEFAULT_PASSWORD

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


class TestFactory:
    async def test_factory_users_can_log_in_through_the_api(self, make, unauthenticated_client):
        user = await make.user()
        resp = await unauthenticated_client.post(
            "/api/auth/login",
            json={"email": user["email"], "password": DEFAULT_PASSWORD, "username": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["id"] == str(user["_id"])

    async def test_factory_users_are_unique(self, make):
        a, b = await make.user(), await make.user()
        assert a["username"] != b["username"] and a["email"] != b["email"]

    async def test_factory_transaction_is_listed_with_its_category(self, make, jwt_client):
        user = await make.user()
        food = await make.category(user, name="Food")
        tx = await make.transaction(user, food, amount=12.5, date=datetime(2026, 1, 31))

        resp = await jwt_client(user).get("/api/transactions")

        assert resp.status_code == 200
        [listed] = resp.json()["data"]
        assert listed["id"] == str(tx["_id"])
        assert listed["amount"] == 12.5
        assert listed["category_name"] == "Food"

    async def test_factory_category_is_listed(self, make, jwt_client):
        user = await make.user()
        cat = await make.category(user, name="Travel", type="income")

        resp = await jwt_client(user).get("/api/categories")

        assert resp.json() == [{
            "id": str(cat["_id"]), "name": "Travel", "type": "income",
            "icon": "tag", "is_default": False,
        }]

    async def test_factory_budget_is_listed_with_spending(self, make, jwt_client):
        user = await make.user()
        food = await make.category(user, name="Food")
        await make.budget(user, food, month_year="2026-01", limit_amount=100)
        await make.transaction(user, food, amount=40, date=datetime(2026, 1, 10))

        resp = await jwt_client(user).get("/api/budgets", params={"month_year": "2026-01"})

        [budget] = resp.json()
        assert budget["category_name"] == "Food"
        assert budget["spent_amount"] == 40
        assert budget["percentage"] == 40


class TestJwtClient:
    async def test_real_token_authenticates(self, make, jwt_client):
        user = await make.user()
        resp = await jwt_client(user).get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == user["email"]

    async def test_can_be_used_alongside_the_override_client(self, make, client, test_user, jwt_client):
        other = await make.user()
        me_override = (await client.get("/api/auth/me")).json()
        me_jwt = (await jwt_client(other).get("/api/auth/me")).json()
        assert me_override["email"] == test_user["email"]
        assert me_jwt["email"] == other["email"]

    async def test_token_for_deleted_user_is_rejected(self, make, db, jwt_client):
        user = await make.user()
        c = jwt_client(user)
        await db.users.delete_one({"_id": user["_id"]})
        assert (await c.get("/api/auth/me")).status_code == 401
