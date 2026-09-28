
from datetime import datetime

import pytest

from app.core.security import create_access_token

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

BAD_ID = "not-an-object-id"
CLIENT_ERROR = range(400, 500)


@pytest.fixture
async def food(make, test_user):
    return await make.category(test_user, name="Food")


class TestInputTheApiAlreadyHandles:
    async def test_malformed_json_body(self, lenient_client):
        resp = await lenient_client.post(
            "/api/transactions", content=b'{"type": "expense",', headers={"Content-Type": "application/json"}
        )
        assert resp.status_code == 422

    async def test_wrong_content_type(self, lenient_client):
        resp = await lenient_client.post("/api/transactions", content=b"amount=5", headers={"Content-Type": "text/plain"})
        assert resp.status_code == 422

    @pytest.mark.parametrize("amount", ["abc", None, [], {}], ids=["text", "null", "list", "object"])
    async def test_non_numeric_amount(self, lenient_client, food, amount):
        resp = await lenient_client.post("/api/transactions", json={
            "type": "expense", "amount": amount, "date": "2026-01-05T00:00:00",
            "category_id": str(food["_id"]), "description": "x",
        })
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "description",
        ["x" * 10_000, "Kafe ☕ и бурек 🥐", "‮reversed text", "<script>alert(1)</script>", "'; DROP TABLE users; --"],
        ids=["10k-chars", "emoji-cyrillic", "rtl-override", "html", "sql-like"],
    )
    async def test_unusual_text_is_stored_and_returned_unchanged(self, lenient_client, food, description):
        resp = await lenient_client.post("/api/transactions", json={
            "type": "expense", "amount": 1, "date": "2026-01-05T00:00:00",
            "category_id": str(food["_id"]), "description": description,
        })
        assert resp.status_code == 201
        assert resp.json()["description"] == description

    async def test_empty_update_body_changes_nothing(self, lenient_client, make, test_user, food, db):
        tx = await make.transaction(test_user, food, amount=12, description="unchanged")
        resp = await lenient_client.put(f"/api/transactions/{tx['_id']}", json={})
        assert resp.status_code == 200
        assert (resp.json()["amount"], resp.json()["description"]) == (12, "unchanged")
        assert await db.transactions.find_one({"_id": tx["_id"]}) == tx

    async def test_unknown_route(self, lenient_client):
        assert (await lenient_client.get("/api/does-not-exist")).status_code == 404

    async def test_wrong_http_method(self, lenient_client):
        assert (await lenient_client.patch("/api/transactions")).status_code == 405


class TestMalformedIds:
    @pytest.mark.xfail(strict=True, reason="a malformed id in the URL crashes the server")
    @pytest.mark.parametrize(
        "method, path, body",
        [
            ("put", f"/api/transactions/{BAD_ID}", {"amount": 5}),
            ("delete", f"/api/transactions/{BAD_ID}", None),
            ("put", f"/api/budgets/{BAD_ID}", {"limit_amount": 5}),
            ("delete", f"/api/budgets/{BAD_ID}", None),
            ("delete", f"/api/categories/{BAD_ID}", None),
        ],
        ids=["update-transaction", "delete-transaction", "update-budget", "delete-budget", "delete-category"],
    )
    async def test_malformed_path_id_is_a_client_error(self, lenient_client, method, path, body):
        kwargs = {"json": body} if body is not None else {}
        resp = await getattr(lenient_client, method)(path, **kwargs)
        assert resp.status_code in CLIENT_ERROR

    @pytest.mark.xfail(strict=True, reason="a token whose subject isn't an ObjectId crashes the server")
    async def test_token_with_a_malformed_subject_is_unauthorised(self, lenient_client):
        token = create_access_token({"sub": BAD_ID})
        resp = await lenient_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestMalformedQueryValues:
    @pytest.mark.xfail(strict=True, reason="an invalid month crashes the server")
    @pytest.mark.parametrize("month_year", ["2026-13", "abc"], ids=["month-13", "text"])
    @pytest.mark.parametrize("path", ["/api/reports", "/api/reports/export/csv"], ids=["report", "csv"])
    async def test_invalid_month_is_a_client_error(self, lenient_client, path, month_year):
        resp = await lenient_client.get(path, params={"month_year": month_year})
        assert resp.status_code in CLIENT_ERROR

    @pytest.mark.xfail(strict=True, reason="an invalid month crashes the server")
    async def test_invalid_month_when_creating_a_budget_is_a_client_error(self, lenient_client, food):
        resp = await lenient_client.post(
            "/api/budgets", json={"category_id": str(food["_id"]), "month_year": "2026-13", "limit_amount": 5}
        )
        assert resp.status_code in CLIENT_ERROR

    @pytest.mark.xfail(strict=True, reason="an unparsable date filter crashes the server")
    @pytest.mark.parametrize("param", ["start_date", "end_date"])
    async def test_unparsable_date_filter_is_a_client_error(self, lenient_client, param):
        resp = await lenient_client.get("/api/transactions", params={param: "yesterday"})
        assert resp.status_code in CLIENT_ERROR

    @pytest.mark.xfail(strict=True, reason="search text is used as a regular expression; '(' crashes the query")
    async def test_search_with_regex_characters_does_not_crash(self, lenient_client):
        resp = await lenient_client.get("/api/transactions", params={"search": "("})
        assert resp.status_code == 200

    @pytest.mark.xfail(strict=True, reason="search text is used as a regular expression, not literal text")
    async def test_search_matches_the_literal_text(self, lenient_client, make, test_user, food):
        await make.transaction(test_user, food, description="1+1=2 maths book", date=datetime(2026, 1, 5))
        resp = await lenient_client.get("/api/transactions", params={"search": "1+1"})
        assert [t["description"] for t in resp.json()["data"]] == ["1+1=2 maths book"]


class TestPoisonedRecords:
    """A malformed category id is stored and then breaks later reads."""

    @pytest.mark.xfail(strict=True, reason="a malformed category id is stored, then the response crashes")
    async def test_transaction_with_malformed_category_is_rejected(self, lenient_client, db):
        resp = await lenient_client.post("/api/transactions", json={
            "type": "expense", "amount": 5, "date": "2026-01-05T00:00:00",
            "category_id": BAD_ID, "description": "bad",
        })
        assert resp.status_code in CLIENT_ERROR
        assert await db.transactions.count_documents({}) == 0

    @pytest.mark.xfail(strict=True, reason="a malformed category id is stored, then the response crashes")
    async def test_budget_with_malformed_category_is_rejected(self, lenient_client, db):
        resp = await lenient_client.post(
            "/api/budgets", json={"category_id": BAD_ID, "month_year": "2026-01", "limit_amount": 5}
        )
        assert resp.status_code in CLIENT_ERROR
        assert await db.budgets.count_documents({}) == 0

    @pytest.mark.xfail(strict=True, reason="one stored malformed category id breaks the list for good")
    @pytest.mark.parametrize("path", ["/api/transactions", "/api/dashboard"], ids=["transactions", "dashboard"])
    async def test_one_bad_record_does_not_break_other_pages(self, lenient_client, make, test_user, food, db, path):
        await make.transaction(test_user, food, description="good", date=datetime.utcnow())
        await db.transactions.insert_one({
            "user_id": str(test_user["_id"]), "type": "expense", "amount": 1,
            "date": datetime.utcnow(), "category_id": BAD_ID, "description": "bad",
        })
        assert (await lenient_client.get(path)).status_code == 200


class TestRegistrationInput:
    @pytest.mark.xfail(strict=True, reason="empty usernames and passwords are accepted")
    @pytest.mark.parametrize(
        "username, password", [("", "pw123456"), ("someone", "")], ids=["empty-username", "empty-password"]
    )
    async def test_empty_credentials_are_rejected(self, unauthenticated_client, username, password):
        resp = await unauthenticated_client.post(
            "/api/auth/register", json={"username": username, "email": "e@example.com", "password": password}
        )
        assert resp.status_code == 422


class TestPasswordBytes:

    @pytest.mark.xfail(strict=True, reason="a NUL byte in a password crashes bcrypt hashing/verification")
    @pytest.mark.parametrize("endpoint", ["register", "login", "change-current", "change-new"])
    async def test_nul_byte_in_a_password_is_a_client_error(self, lenient_client, endpoint):
        bad = "pass\x00word"
        requests = {
            "register": ("/api/auth/register", {"username": "nul", "email": "nul@example.com", "password": bad}),
            "login": ("/api/auth/login", {"email": "testuser@example.com", "password": bad, "username": ""}),
            "change-current": ("/api/auth/change-password", {"current_password": bad, "new_password": "fine-1"}),
            "change-new": ("/api/auth/change-password", {"current_password": "testpassword123", "new_password": bad}),
        }
        path, body = requests[endpoint]
        assert (await lenient_client.post(path, json=body)).status_code in CLIENT_ERROR
