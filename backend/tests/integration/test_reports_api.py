
import csv
import io
from datetime import datetime, timezone

import pytest
import time_machine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]

JAN = "2026-01"
CSV_HEADER = ["Date", "Type", "Description", "Amount", "Category", "Payment Method", "Merchant"]


def rows_of(resp) -> list:
    return list(csv.reader(io.StringIO(resp.text, newline="")))


@pytest.fixture
async def food(make, test_user):
    return await make.category(test_user, name="Food")


@pytest.fixture
async def salary(make, test_user):
    return await make.category(test_user, name="Salary", type="income")


class TestReport:
    async def test_monthly_figures(self, client, make, test_user, food, salary):
        await make.transaction(test_user, salary, amount=3000, date=datetime(2026, 1, 1))
        await make.transaction(test_user, food, amount=120, date=datetime(2026, 1, 5), description="Groceries")
        await make.transaction(test_user, food, amount=30, date=datetime(2026, 1, 9), description="Lunch")

        resp = await client.get("/api/reports", params={"month_year": JAN})

        assert resp.status_code == 200
        assert resp.json() == {
            "month_year": JAN,
            "total_income": 3000,
            "total_expenses": 150,
            "savings": 2850,
            "savings_rate": 95,
            "largest_expense": {"description": "Groceries", "amount": 120},
            "top_spending_category": "Food",
        }

    async def test_raw_transactions_are_not_exposed(self, client, make, test_user, food):
        await make.transaction(test_user, food, date=datetime(2026, 1, 5))
        body = (await client.get("/api/reports", params={"month_year": JAN})).json()
        assert "transactions" not in body

    async def test_other_months_are_excluded(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=50, date=datetime(2025, 12, 31, 23, 59, 59))
        await make.transaction(test_user, food, amount=60, date=datetime(2026, 2, 1))
        body = (await client.get("/api/reports", params={"month_year": JAN})).json()
        assert body["total_expenses"] == 0
        assert body["largest_expense"] is None

    async def test_other_users_transactions_are_excluded(self, client, make, other_user):
        cat = await make.category(other_user)
        await make.transaction(other_user, cat, amount=999, date=datetime(2026, 1, 5))
        body = (await client.get("/api/reports", params={"month_year": JAN})).json()
        assert body["total_expenses"] == 0

    async def test_without_month_the_current_month_is_used(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=10, date=datetime(2026, 3, 20))
        await make.transaction(test_user, food, amount=99, date=datetime(2026, 2, 20))

        with time_machine.travel(datetime(2026, 3, 25, tzinfo=timezone.utc), tick=False):
            body = (await client.get("/api/reports")).json()

        assert body["month_year"] == "2026-03"
        assert body["total_expenses"] == 10

    @pytest.mark.xfail(strict=True, reason="report totals silently stop after 1000 transactions in a month")
    async def test_all_transactions_in_a_busy_month_are_counted(self, client, db, test_user, food):
        await db.transactions.insert_many([
            {"user_id": str(test_user["_id"]), "type": "expense", "amount": 1.0,
             "date": datetime(2026, 1, 15), "category_id": str(food["_id"]), "description": f"tx{i}"}
            for i in range(1001)
        ])
        body = (await client.get("/api/reports", params={"month_year": JAN})).json()
        assert body["total_expenses"] == 1001


class TestCsvExport:
    async def test_download_headers_and_file_name(self, client):
        resp = await client.get("/api/reports/export/csv", params={"month_year": JAN})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert resp.headers["content-disposition"] == "attachment; filename=report_2026-01.csv"

    async def test_empty_month_has_only_the_header_row(self, client):
        resp = await client.get("/api/reports/export/csv", params={"month_year": JAN})
        assert rows_of(resp) == [CSV_HEADER]

    async def test_one_row_per_transaction_with_all_columns(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=12.5, date=datetime(2026, 1, 7, 18, 30),
                               description="Pizza", payment_method="card", merchant="Luigi's")

        header, row = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))

        assert header == CSV_HEADER
        assert row == ["2026-01-07", "expense", "Pizza", "12.5", "Food", "card", "Luigi's"]

    async def test_missing_optional_values_are_empty_cells(self, client, make, test_user, food):
        await make.transaction(test_user, food, date=datetime(2026, 1, 7), payment_method=None, merchant=None)
        _, row = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))
        assert row[5:] == ["", ""]

    async def test_deleted_category_is_exported_as_unknown(self, client, make, test_user, food, db):
        await make.transaction(test_user, food, date=datetime(2026, 1, 7))
        await db.categories.delete_one({"_id": food["_id"]})
        _, row = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))
        assert row[4] == "Unknown"

    async def test_uncategorised_transaction_is_exported_as_unknown(self, client, make, test_user):
        await make.transaction(test_user, None, date=datetime(2026, 1, 7))
        _, row = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))
        assert row[4] == "Unknown"

    async def test_only_the_users_own_month_is_exported(self, client, make, test_user, other_user, food):
        await make.transaction(test_user, food, date=datetime(2026, 1, 7), description="mine")
        await make.transaction(test_user, food, date=datetime(2026, 2, 7), description="next month")
        cat = await make.category(other_user)
        await make.transaction(other_user, cat, date=datetime(2026, 1, 7), description="theirs")

        rows = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))

        assert [r[2] for r in rows[1:]] == ["mine"]

    async def test_without_month_the_current_month_is_exported(self, client):
        with time_machine.travel(datetime(2026, 12, 31, 23, tzinfo=timezone.utc), tick=False):
            resp = await client.get("/api/reports/export/csv")
        assert resp.headers["content-disposition"] == "attachment; filename=report_2026-12.csv"

    @pytest.mark.xfail(strict=True, reason="cells that start with = + - @ are exported as spreadsheet formulas")
    async def test_formula_like_text_is_neutralised(self, client, make, test_user, food):
        await make.transaction(test_user, food, date=datetime(2026, 1, 7), description='=HYPERLINK("http://x","y")')
        _, row = rows_of(await client.get("/api/reports/export/csv", params={"month_year": JAN}))
        assert not row[2].startswith("=")


class TestAuthenticationRequired:
    @pytest.mark.parametrize("path", ["/api/reports", "/api/reports/export/csv"], ids=["report", "csv"])
    async def test_requests_without_a_token_are_rejected(self, unauthenticated_client, path):
        assert (await unauthenticated_client.get(path)).status_code == 401
