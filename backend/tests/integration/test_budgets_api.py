
from datetime import datetime

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

JAN = "2026-01"


async def list_budgets(client, month_year=JAN) -> list:
    resp = await client.get("/api/budgets", params={"month_year": month_year})
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def food(make, test_user):
    return await make.category(test_user, name="Food", icon="utensils")


class TestSpendingCalculation:
    async def test_expenses_in_the_category_and_month_are_summed(self, client, make, test_user, food):
        await make.budget(test_user, food, month_year=JAN, limit_amount=200)
        await make.transaction(test_user, food, amount=30, date=datetime(2026, 1, 5))
        await make.transaction(test_user, food, amount=45.5, date=datetime(2026, 1, 20))

        [budget] = await list_budgets(client)

        assert budget["spent_amount"] == 75.5
        assert budget["percentage"] == pytest.approx(37.75)
        assert budget["category_name"] == "Food"
        assert budget["category_icon"] == "utensils"

    @pytest.mark.parametrize(
        "date, counts",
        [
            (datetime(2025, 12, 31, 23, 59, 59), False),
            (datetime(2026, 1, 1, 0, 0, 0), True),
            (datetime(2026, 1, 31, 23, 59, 59), True),
            (datetime(2026, 2, 1, 0, 0, 0), False),
        ],
        ids=["dec-31-23:59:59", "jan-1-00:00", "jan-31-23:59:59", "feb-1-00:00"],
    )
    async def test_month_boundaries(self, client, make, test_user, food, date, counts):
        await make.budget(test_user, food, month_year=JAN)
        await make.transaction(test_user, food, amount=10, date=date)

        [budget] = await list_budgets(client)

        assert budget["spent_amount"] == (10 if counts else 0)

    async def test_income_in_the_same_category_does_not_count(self, client, make, test_user, food):
        await make.budget(test_user, food, month_year=JAN)
        await make.transaction(test_user, food, type="income", amount=500, date=datetime(2026, 1, 5))

        [budget] = await list_budgets(client)

        assert budget["spent_amount"] == 0

    async def test_expenses_in_other_categories_do_not_count(self, client, make, test_user, food):
        rent = await make.category(test_user, name="Rent")
        await make.budget(test_user, food, month_year=JAN)
        await make.transaction(test_user, rent, amount=900, date=datetime(2026, 1, 5))

        [budget] = await list_budgets(client)

        assert budget["spent_amount"] == 0

    async def test_other_users_expenses_do_not_count(self, client, make, test_user, other_user, food):
        await make.budget(test_user, food, month_year=JAN)
        await make.transaction(other_user, food, amount=70, date=datetime(2026, 1, 5))

        [budget] = await list_budgets(client)

        assert budget["spent_amount"] == 0

    async def test_over_budget_is_capped_at_100_percent_but_amounts_are_real(self, client, make, test_user, food):
        await make.budget(test_user, food, month_year=JAN, limit_amount=100)
        await make.transaction(test_user, food, amount=150, date=datetime(2026, 1, 5))

        [budget] = await list_budgets(client)

        assert budget["percentage"] == 100
        assert budget["spent_amount"] == 150
        assert budget["limit_amount"] == 100

    async def test_recalculated_spending_is_saved(self, client, make, test_user, food, db):
        budget = await make.budget(test_user, food, month_year=JAN, spent_amount=0)
        await make.transaction(test_user, food, amount=42, date=datetime(2026, 1, 5))

        await list_budgets(client)

        stored = await db.budgets.find_one({"_id": budget["_id"]})
        assert stored["spent_amount"] == 42


class TestListBudgets:
    async def test_only_the_requested_month_is_listed(self, client, make, test_user, food):
        jan = await make.budget(test_user, food, month_year="2026-01")
        await make.budget(test_user, food, month_year="2026-02")

        assert [b["id"] for b in await list_budgets(client, "2026-01")] == [str(jan["_id"])]

    async def test_only_the_users_own_budgets_are_listed(self, client, make, test_user, other_user, food):
        mine = await make.budget(test_user, food, month_year=JAN)
        theirs_cat = await make.category(other_user)
        await make.budget(other_user, theirs_cat, month_year=JAN)

        assert [b["id"] for b in await list_budgets(client)] == [str(mine["_id"])]

    async def test_without_month_the_current_month_is_used(self, client, make, test_user, food):
        before = datetime.utcnow()
        current = f"{before.year}-{before.month:02d}"
        this_month = await make.budget(test_user, food, month_year=current)
        await make.budget(test_user, food, month_year="2000-01")

        resp = await client.get("/api/budgets")

        after = datetime.utcnow()
        if (after.year, after.month) != (before.year, before.month):
            pytest.skip("month changed during the test")
        assert [b["id"] for b in resp.json()] == [str(this_month["_id"])]

    async def test_month_without_budgets_is_empty(self, client):
        assert await list_budgets(client, "2031-05") == []


class TestCreateBudget:
    async def test_creates_a_budget_with_current_spending(self, client, make, test_user, food, db):
        await make.transaction(test_user, food, amount=25, date=datetime(2026, 1, 3))

        resp = await client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": JAN, "limit_amount": 100}
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["spent_amount"] == 25
        assert body["percentage"] == 25
        assert body["category_name"] == "Food"
        stored = await db.budgets.find_one({})
        assert stored["user_id"] == str(test_user["_id"])

    async def test_duplicate_category_and_month_is_rejected(self, client, make, test_user, food, db):
        await make.budget(test_user, food, month_year=JAN)

        resp = await client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": JAN, "limit_amount": 50}
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Budget already exists for this category and month"
        assert await db.budgets.count_documents({}) == 1

    async def test_same_category_in_another_month_is_allowed(self, client, make, test_user, food):
        await make.budget(test_user, food, month_year=JAN)
        resp = await client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": "2026-02", "limit_amount": 50}
        )
        assert resp.status_code == 201

    async def test_another_user_can_budget_the_same_category_id_and_month(self, client, make, other_user, food):
        await make.budget(other_user, food, month_year=JAN)
        resp = await client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": JAN, "limit_amount": 50}
        )
        assert resp.status_code == 201

    @pytest.mark.parametrize(
        "limit, status",
        [(-0.01, 422), (0, 422), (0.01, 201), (1_000_000_000, 201)],
        ids=["negative", "zero", "one-cent", "very-large"],
    )
    async def test_limit_amount_boundaries(self, client, food, limit, status):
        resp = await client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": JAN, "limit_amount": limit}
        )
        assert resp.status_code == status

    @pytest.mark.parametrize("missing", ["category_id", "month_year", "limit_amount"])
    async def test_missing_field_is_rejected(self, client, food, missing):
        payload = {"category_id": str(food["_id"]), "month_year": JAN, "limit_amount": 50}
        del payload[missing]
        assert (await client.post("/api/budgets", json=payload)).status_code == 422

    @pytest.mark.xfail(strict=True, reason="budgets are accepted for categories that don't exist")
    async def test_category_must_exist(self, client, new_object_id):
        resp = await client.post(
            "/api/budgets", json={"category_id": str(new_object_id), "month_year": JAN, "limit_amount": 50}
        )
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.xfail(strict=True, reason="budgets are accepted for another user's category")
    async def test_category_must_belong_to_the_user(self, client, make, other_user):
        theirs = await make.category(other_user, name="Theirs")
        resp = await client.post(
            "/api/budgets", json={"category_id": str(theirs["_id"]), "month_year": JAN, "limit_amount": 50}
        )
        assert resp.status_code in (400, 404, 422)


class TestUpdateBudget:
    async def test_changes_the_limit_and_recomputes_the_percentage(self, client, make, test_user, food, db):
        budget = await make.budget(test_user, food, limit_amount=100, spent_amount=50)

        resp = await client.put(f"/api/budgets/{budget['_id']}", json={"limit_amount": 200})

        assert resp.status_code == 200
        assert resp.json()["limit_amount"] == 200
        assert resp.json()["percentage"] == 25
        assert (await db.budgets.find_one({"_id": budget["_id"]}))["limit_amount"] == 200

    @pytest.mark.parametrize("limit", [0, -5], ids=["zero", "negative"])
    async def test_non_positive_limit_is_rejected(self, client, make, test_user, food, limit):
        budget = await make.budget(test_user, food)
        assert (await client.put(f"/api/budgets/{budget['_id']}", json={"limit_amount": limit})).status_code == 422

    async def test_nonexistent_budget_returns_404(self, client, new_object_id):
        assert (await client.put(f"/api/budgets/{new_object_id}", json={"limit_amount": 10})).status_code == 404

    async def test_other_users_budget_returns_404_and_is_unchanged(self, client, make, other_user, db):
        cat = await make.category(other_user)
        theirs = await make.budget(other_user, cat, limit_amount=100)

        resp = await client.put(f"/api/budgets/{theirs['_id']}", json={"limit_amount": 1})

        assert resp.status_code == 404
        assert (await db.budgets.find_one({"_id": theirs["_id"]}))["limit_amount"] == 100

    @pytest.mark.xfail(strict=True, reason="update reports the spending saved at the last list, not the current one")
    async def test_update_reflects_current_spending(self, client, make, test_user, food):
        budget = await make.budget(test_user, food, month_year=JAN, limit_amount=100, spent_amount=0)
        await make.transaction(test_user, food, amount=60, date=datetime(2026, 1, 5))

        resp = await client.put(f"/api/budgets/{budget['_id']}", json={"limit_amount": 120})

        assert resp.json()["spent_amount"] == 60


class TestDeleteBudget:
    async def test_deletes_the_budget(self, client, make, test_user, food, db):
        budget = await make.budget(test_user, food)
        assert (await client.delete(f"/api/budgets/{budget['_id']}")).status_code == 204
        assert await db.budgets.count_documents({}) == 0

    async def test_nonexistent_budget_returns_404(self, client, new_object_id):
        assert (await client.delete(f"/api/budgets/{new_object_id}")).status_code == 404

    async def test_other_users_budget_returns_404_and_is_kept(self, client, make, other_user, db):
        cat = await make.category(other_user)
        theirs = await make.budget(other_user, cat)
        assert (await client.delete(f"/api/budgets/{theirs['_id']}")).status_code == 404
        assert await db.budgets.count_documents({}) == 1

    async def test_deleting_twice_returns_404_the_second_time(self, client, make, test_user, food):
        budget = await make.budget(test_user, food)
        await client.delete(f"/api/budgets/{budget['_id']}")
        assert (await client.delete(f"/api/budgets/{budget['_id']}")).status_code == 404


class TestAuthenticationRequired:
    @pytest.mark.parametrize(
        "method, path",
        [
            ("get", "/api/budgets"),
            ("post", "/api/budgets"),
            ("put", "/api/budgets/000000000000000000000000"),
            ("delete", "/api/budgets/000000000000000000000000"),
        ],
        ids=["list", "create", "update", "delete"],
    )
    async def test_requests_without_a_token_are_rejected(self, unauthenticated_client, method, path):
        kwargs = {"json": {"category_id": "x", "month_year": JAN, "limit_amount": 1}} if method in ("post", "put") else {}
        resp = await getattr(unauthenticated_client, method)(path, **kwargs)
        assert resp.status_code == 401
