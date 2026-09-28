
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


class TestCreateTransaction:
    async def test_create_returns_201_and_enriched_transaction(self, client, tx_payload, category):
        resp = await client.post("/api/transactions", json=tx_payload())

        assert resp.status_code == 201
        body = resp.json()
        assert body["description"] == "Groceries"
        assert body["amount"] == 25.5
        assert body["category_name"] == category["name"]
        assert "id" in body

    async def test_created_transaction_is_persisted_and_retrievable(self, client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload(description="Rent"))
        tx_id = create_resp.json()["id"]

        list_resp = await client.get("/api/transactions")

        descriptions = [t["description"] for t in list_resp.json()["data"]]
        assert "Rent" in descriptions
        assert any(t["id"] == tx_id for t in list_resp.json()["data"])

    async def test_create_rejects_non_positive_amount(self, client, tx_payload):
        resp = await client.post("/api/transactions", json=tx_payload(amount=0))
        assert resp.status_code == 422

    async def test_create_rejects_invalid_type(self, client, tx_payload):
        resp = await client.post("/api/transactions", json=tx_payload(type="not-a-type"))
        assert resp.status_code == 422

    async def test_create_rejects_missing_required_field(self, client, tx_payload):
        payload = tx_payload()
        del payload["description"]
        resp = await client.post("/api/transactions", json=payload)
        assert resp.status_code == 422

    async def test_create_income_transaction(self, client, tx_payload):
        resp = await client.post("/api/transactions", json=tx_payload(type="income", description="Paycheck"))
        assert resp.status_code == 201
        assert resp.json()["type"] == "income"


class TestListTransactions:
    async def test_list_empty_returns_zero_total(self, client):
        resp = await client.get("/api/transactions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["data"] == []

    async def test_list_returns_created_transactions(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="A"))
        await client.post("/api/transactions", json=tx_payload(description="B"))

        resp = await client.get("/api/transactions")

        assert resp.json()["total"] == 2


class TestUpdateTransaction:
    async def test_update_changes_fields(self, client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload(description="Old"))
        tx_id = create_resp.json()["id"]

        resp = await client.put(f"/api/transactions/{tx_id}", json={"description": "New description"})

        assert resp.status_code == 200
        assert resp.json()["description"] == "New description"

    async def test_update_only_touches_provided_fields(self, client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload(description="Keep me", amount=99.0))
        tx_id = create_resp.json()["id"]

        resp = await client.put(f"/api/transactions/{tx_id}", json={"amount": 150.0})

        assert resp.status_code == 200
        assert resp.json()["amount"] == 150.0
        assert resp.json()["description"] == "Keep me"

    async def test_update_nonexistent_transaction_returns_404(self, client):
        resp = await client.put("/api/transactions/64b7f9c9f9c9f9c9f9c9f9c9", json={"description": "x"})
        assert resp.status_code == 404

    async def test_update_rejects_non_positive_amount(self, client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload())
        tx_id = create_resp.json()["id"]

        resp = await client.put(f"/api/transactions/{tx_id}", json={"amount": -10})
        assert resp.status_code == 422

    async def test_cannot_update_another_users_transaction(self, client, other_client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload())
        tx_id = create_resp.json()["id"]

        resp = await other_client.put(f"/api/transactions/{tx_id}", json={"description": "hijacked"})

        assert resp.status_code == 404


class TestDeleteTransaction:
    async def test_delete_removes_transaction(self, client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload())
        tx_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/transactions/{tx_id}")
        assert delete_resp.status_code == 204

        list_resp = await client.get("/api/transactions")
        assert list_resp.json()["total"] == 0

    async def test_delete_nonexistent_transaction_returns_404(self, client):
        resp = await client.delete("/api/transactions/64b7f9c9f9c9f9c9f9c9f9c9")
        assert resp.status_code == 404

    async def test_cannot_delete_another_users_transaction(self, client, other_client, tx_payload):
        create_resp = await client.post("/api/transactions", json=tx_payload())
        tx_id = create_resp.json()["id"]

        resp = await other_client.delete(f"/api/transactions/{tx_id}")

        assert resp.status_code == 404
        list_resp = await client.get("/api/transactions")
        assert list_resp.json()["total"] == 1


class TestPagination:
    async def test_page_size_limits_results(self, client, tx_payload):
        for i in range(5):
            await client.post("/api/transactions", json=tx_payload(description=f"Item {i}"))

        resp = await client.get("/api/transactions", params={"page": 1, "page_size": 2})

        body = resp.json()
        assert body["total"] == 5
        assert len(body["data"]) == 2
        assert body["page"] == 1
        assert body["page_size"] == 2

    async def test_second_page_returns_remaining_items(self, client, tx_payload):
        for i in range(5):
            await client.post("/api/transactions", json=tx_payload(description=f"Item {i}"))

        resp = await client.get("/api/transactions", params={"page": 2, "page_size": 2})

        assert len(resp.json()["data"]) == 2

    async def test_page_beyond_available_data_returns_empty(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload())

        resp = await client.get("/api/transactions", params={"page": 5, "page_size": 10})

        assert resp.json()["data"] == []
        assert resp.json()["total"] == 1

    async def test_page_size_over_max_is_rejected(self, client):
        resp = await client.get("/api/transactions", params={"page_size": 1000})
        assert resp.status_code == 422

    async def test_page_below_one_is_rejected(self, client):
        resp = await client.get("/api/transactions", params={"page": 0})
        assert resp.status_code == 422


class TestSearch:
    async def test_search_matches_description(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="Weekly groceries"))
        await client.post("/api/transactions", json=tx_payload(description="Gym membership"))

        resp = await client.get("/api/transactions", params={"search": "groceries"})

        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["description"] == "Weekly groceries"

    async def test_search_matches_merchant(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="Coffee", merchant="Blue Bottle"))
        await client.post("/api/transactions", json=tx_payload(description="Lunch", merchant="Chipotle"))

        resp = await client.get("/api/transactions", params={"search": "Bottle"})

        assert resp.json()["total"] == 1

    async def test_search_is_case_insensitive(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="Weekly Groceries"))

        resp = await client.get("/api/transactions", params={"search": "GROCERIES"})

        assert resp.json()["total"] == 1

    async def test_search_no_match_returns_empty(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="Weekly groceries"))

        resp = await client.get("/api/transactions", params={"search": "nonexistent-term"})

        assert resp.json()["total"] == 0


class TestFiltering:
    async def test_filter_by_type(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(type="expense", description="Expense one"))
        await client.post("/api/transactions", json=tx_payload(type="income", description="Income one"))

        resp = await client.get("/api/transactions", params={"type": "income"})

        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["type"] == "income"

    async def test_filter_by_category_id(self, client, db, test_user, tx_payload, category):
        other_cat = await db.categories.insert_one({
            "name": "Transport", "type": "expense", "user_id": str(test_user["_id"]), "is_default": False,
        })
        await client.post("/api/transactions", json=tx_payload(category_id=str(category["_id"]), description="Food tx"))
        await client.post("/api/transactions", json=tx_payload(category_id=str(other_cat.inserted_id), description="Transport tx"))

        resp = await client.get("/api/transactions", params={"category_id": str(category["_id"])})

        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["description"] == "Food tx"


class TestSorting:
    async def test_sort_by_amount_ascending(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(amount=50, description="Mid"))
        await client.post("/api/transactions", json=tx_payload(amount=10, description="Low"))
        await client.post("/api/transactions", json=tx_payload(amount=90, description="High"))

        resp = await client.get("/api/transactions", params={"sort_by": "amount", "sort_order": "asc"})

        amounts = [t["amount"] for t in resp.json()["data"]]
        assert amounts == sorted(amounts)

    async def test_sort_by_amount_descending(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(amount=50, description="Mid"))
        await client.post("/api/transactions", json=tx_payload(amount=10, description="Low"))
        await client.post("/api/transactions", json=tx_payload(amount=90, description="High"))

        resp = await client.get("/api/transactions", params={"sort_by": "amount", "sort_order": "desc"})

        amounts = [t["amount"] for t in resp.json()["data"]]
        assert amounts == sorted(amounts, reverse=True)

    async def test_default_sort_is_by_date_descending(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(date="2026-01-01T00:00:00", description="Oldest"))
        await client.post("/api/transactions", json=tx_payload(date="2026-03-01T00:00:00", description="Newest"))

        resp = await client.get("/api/transactions")

        data = resp.json()["data"]
        assert data[0]["description"] == "Newest"


class TestDateFiltering:
    async def test_start_date_excludes_earlier_transactions(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(date="2026-01-01T00:00:00", description="January"))
        await client.post("/api/transactions", json=tx_payload(date="2026-03-01T00:00:00", description="March"))

        resp = await client.get("/api/transactions", params={"start_date": "2026-02-01T00:00:00"})

        descriptions = [t["description"] for t in resp.json()["data"]]
        assert descriptions == ["March"]

    async def test_end_date_excludes_later_transactions(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(date="2026-01-01T00:00:00", description="January"))
        await client.post("/api/transactions", json=tx_payload(date="2026-03-01T00:00:00", description="March"))

        resp = await client.get("/api/transactions", params={"end_date": "2026-02-01T00:00:00"})

        descriptions = [t["description"] for t in resp.json()["data"]]
        assert descriptions == ["January"]

    async def test_start_and_end_date_together_defines_a_range(self, client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(date="2026-01-01T00:00:00", description="January"))
        await client.post("/api/transactions", json=tx_payload(date="2026-02-15T00:00:00", description="Mid-Feb"))
        await client.post("/api/transactions", json=tx_payload(date="2026-03-01T00:00:00", description="March"))

        resp = await client.get(
            "/api/transactions",
            params={"start_date": "2026-02-01T00:00:00", "end_date": "2026-02-28T00:00:00"},
        )

        descriptions = [t["description"] for t in resp.json()["data"]]
        assert descriptions == ["Mid-Feb"]


class TestAuthenticationRequired:
    async def test_list_without_token_returns_401(self, unauthenticated_client):
        resp = await unauthenticated_client.get("/api/transactions")
        assert resp.status_code == 401

    async def test_create_without_token_returns_401(self, unauthenticated_client, tx_payload):
        resp = await unauthenticated_client.post("/api/transactions", json=tx_payload())
        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, unauthenticated_client, tx_payload):
        resp = await unauthenticated_client.get(
            "/api/transactions", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert resp.status_code == 401


class TestUserIsolation:
    async def test_users_only_see_their_own_transactions(self, client, other_client, tx_payload):
        await client.post("/api/transactions", json=tx_payload(description="Mine"))
        await other_client.post("/api/transactions", json=tx_payload(description="Theirs"))

        mine = await client.get("/api/transactions")
        theirs = await other_client.get("/api/transactions")

        assert [t["description"] for t in mine.json()["data"]] == ["Mine"]
        assert [t["description"] for t in theirs.json()["data"]] == ["Theirs"]

    async def test_cannot_retrieve_missing_transaction_owned_by_other_user_as_own(self, client, other_client, tx_payload):
        create_resp = await other_client.post("/api/transactions", json=tx_payload())
        tx_id = create_resp.json()["id"]

        resp = await client.get("/api/transactions")

        ids = [t["id"] for t in resp.json()["data"]]
        assert tx_id not in ids
