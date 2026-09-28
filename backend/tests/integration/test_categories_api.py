
from datetime import datetime

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


class TestListCategories:
    async def test_new_user_sees_the_fourteen_seeded_defaults(self, unauthenticated_client):
        reg = await unauthenticated_client.post(
            "/api/auth/register",
            json={"username": "newbie", "email": "newbie@example.com", "password": "pw123456"},
        )
        token = reg.json()["access_token"]

        resp = await unauthenticated_client.get("/api/categories", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        cats = resp.json()
        assert len(cats) == 14
        assert all(c["is_default"] for c in cats)
        assert {c["type"] for c in cats} == {"income", "expense"}

    async def test_lists_only_the_users_own_categories(self, client, test_user, other_user, make):
        mine = await make.category(test_user, name="Mine")
        await make.category(other_user, name="Theirs")

        resp = await client.get("/api/categories")

        assert [c["id"] for c in resp.json()] == [str(mine["_id"])]

    async def test_empty_list_for_a_user_without_categories(self, client):
        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_up_to_200_categories_are_listed(self, client, test_user, db):
        await db.categories.insert_many(
            [{"name": f"C{i}", "type": "expense", "user_id": str(test_user["_id"])} for i in range(200)]
        )
        assert len((await client.get("/api/categories")).json()) == 200

    @pytest.mark.xfail(strict=True, reason="the list silently stops at 200 categories")
    async def test_more_than_200_categories_are_all_listed(self, client, test_user, db):
        await db.categories.insert_many(
            [{"name": f"C{i}", "type": "expense", "user_id": str(test_user["_id"])} for i in range(201)]
        )
        assert len((await client.get("/api/categories")).json()) == 201


class TestCreateCategory:
    @pytest.mark.parametrize("type_", ["income", "expense"])
    async def test_creates_a_custom_category(self, client, type_):
        resp = await client.post("/api/categories", json={"name": "Pets", "type": type_, "icon": "paw"})

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Pets"
        assert body["type"] == type_
        assert body["icon"] == "paw"
        assert body["is_default"] is False
        assert body["id"]

    async def test_icon_defaults_to_tag(self, client):
        resp = await client.post("/api/categories", json={"name": "Misc", "type": "expense"})
        assert resp.json()["icon"] == "tag"

    async def test_created_category_is_stored_for_the_user(self, client, test_user, db):
        body = (await client.post("/api/categories", json={"name": "Pets", "type": "expense"})).json()

        listed = (await client.get("/api/categories")).json()
        assert [c["id"] for c in listed] == [body["id"]]
        stored = await db.categories.find_one({"name": "Pets"})
        assert stored["user_id"] == str(test_user["_id"])
        assert isinstance(stored["created_at"], datetime)

    async def test_is_default_cannot_be_set_by_the_client(self, client):
        resp = await client.post("/api/categories", json={"name": "Sneaky", "type": "expense", "is_default": True})
        assert resp.status_code == 201
        assert resp.json()["is_default"] is False

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "X", "type": "transfer"},
            {"name": "X", "type": ""},
            {"name": "X"},
            {"type": "expense"},
            {},
        ],
        ids=["unknown-type", "empty-type", "missing-type", "missing-name", "empty-body"],
    )
    async def test_invalid_payload_is_rejected(self, client, payload):
        assert (await client.post("/api/categories", json=payload)).status_code == 422


class TestDeleteCategory:
    async def test_deletes_a_custom_category(self, client, test_user, make, db):
        cat = await make.category(test_user)

        resp = await client.delete(f"/api/categories/{cat['_id']}")

        assert resp.status_code == 204
        assert await db.categories.count_documents({}) == 0

    async def test_default_categories_cannot_be_deleted(self, client, test_user, make, db):
        cat = await make.category(test_user, is_default=True)

        resp = await client.delete(f"/api/categories/{cat['_id']}")

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Cannot delete default categories"
        assert await db.categories.count_documents({}) == 1

    async def test_nonexistent_category_returns_404(self, client, new_object_id):
        assert (await client.delete(f"/api/categories/{new_object_id}")).status_code == 404

    async def test_other_users_category_returns_404_and_is_kept(self, client, other_user, make, db):
        theirs = await make.category(other_user)

        resp = await client.delete(f"/api/categories/{theirs['_id']}")

        assert resp.status_code == 404
        assert await db.categories.count_documents({"_id": theirs["_id"]}) == 1

    async def test_deleting_twice_returns_404_the_second_time(self, client, test_user, make):
        cat = await make.category(test_user)
        await client.delete(f"/api/categories/{cat['_id']}")
        assert (await client.delete(f"/api/categories/{cat['_id']}")).status_code == 404

    async def test_transactions_and_budgets_of_a_deleted_category_show_unknown(self, client, test_user, make):
        cat = await make.category(test_user, name="Gone")
        await make.transaction(test_user, cat, date=datetime(2026, 1, 10))
        await make.budget(test_user, cat, month_year="2026-01")

        await client.delete(f"/api/categories/{cat['_id']}")

        [tx] = (await client.get("/api/transactions")).json()["data"]
        [budget] = (await client.get("/api/budgets", params={"month_year": "2026-01"})).json()
        assert tx["category_name"] == "Unknown"
        assert budget["category_name"] == "Unknown"


class TestAuthenticationRequired:
    @pytest.mark.parametrize(
        "method, path",
        [("get", "/api/categories"), ("post", "/api/categories"), ("delete", "/api/categories/000000000000000000000000")],
        ids=["list", "create", "delete"],
    )
    async def test_requests_without_a_token_are_rejected(self, unauthenticated_client, method, path):
        kwargs = {"json": {"name": "X", "type": "expense"}} if method == "post" else {}
        resp = await getattr(unauthenticated_client, method)(path, **kwargs)
        assert resp.status_code == 401
