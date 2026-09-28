
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.routers.reports import get_report_data

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

FOOD, RENT = ObjectId(), ObjectId()


def tx(type_: str, amount: float, category=None, description: str = "tx") -> dict:
    return {
        "_id": ObjectId(),
        "user_id": "user-1",
        "type": type_,
        "amount": amount,
        "date": datetime(2026, 1, 15),
        "category_id": str(category) if category else "",
        "description": description,
    }


def month_contains(mock_db, transactions: list) -> MagicMock:
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=transactions)
    mock_db.transactions.find = MagicMock(return_value=cursor)
    return mock_db.transactions.find


async def report(mock_db, transactions: list, month_year: str = "2026-01") -> dict:
    month_contains(mock_db, transactions)
    return await get_report_data(mock_db, "user-1", month_year)


class TestQuery:
    @pytest.mark.parametrize(
        "month_year, start, end",
        [
            ("2026-01", datetime(2026, 1, 1), datetime(2026, 2, 1)),
            ("2026-12", datetime(2026, 12, 1), datetime(2027, 1, 1)),
        ],
        ids=["jan", "dec->next-year"],
    )
    async def test_reads_only_this_users_transactions_in_the_month(self, mock_db, month_year, start, end):
        find = month_contains(mock_db, [])
        await get_report_data(mock_db, "user-1", month_year)
        assert find.call_args.args[0] == {"user_id": "user-1", "date": {"$gte": start, "$lt": end}}

    @pytest.mark.parametrize("month_year", ["2026-13", "abc"], ids=["month-13", "text"])
    async def test_invalid_month_year_raises_value_error(self, mock_db, month_year):
        month_contains(mock_db, [])
        with pytest.raises(ValueError):
            await get_report_data(mock_db, "user-1", month_year)


class TestEmptyMonth:
    async def test_everything_is_zero_or_empty(self, mock_db):
        result = await report(mock_db, [])
        assert result == {
            "month_year": "2026-01",
            "total_income": 0,
            "total_expenses": 0,
            "savings": 0,
            "savings_rate": 0,
            "largest_expense": None,
            "top_spending_category": "N/A",
            "transactions": [],
        }


class TestTotalsAndSavingsRate:
    async def test_income_and_expenses_are_summed_separately(self, mock_db):
        result = await report(mock_db, [tx("income", 1000), tx("income", 500), tx("expense", 200), tx("expense", 100)])
        assert result["total_income"] == 1500
        assert result["total_expenses"] == 300
        assert result["savings"] == 1200

    @pytest.mark.parametrize(
        "income, expenses, expected_rate",
        [
            (1000, 250, 75),
            (1000, 0, 100),
            (1000, 1000, 0),
            (1000, 1000.01, -0.001),
            (1000, 1500, -50),
        ],
        ids=["typical", "income-only", "break-even", "just-over", "overspent"],
    )
    async def test_savings_rate_is_savings_over_income(self, mock_db, income, expenses, expected_rate):
        transactions = [tx("income", income)] + ([tx("expense", expenses)] if expenses else [])
        result = await report(mock_db, transactions)
        assert result["savings_rate"] == pytest.approx(expected_rate)

    async def test_no_income_gives_zero_rate_instead_of_dividing_by_zero(self, mock_db):
        result = await report(mock_db, [tx("expense", 80)])
        assert result["savings"] == -80
        assert result["savings_rate"] == 0

    @pytest.mark.xfail(strict=True, reason="amounts are summed as binary floats, so cents can drift")
    async def test_totals_are_exact_to_the_cent(self, mock_db):
        result = await report(mock_db, [tx("expense", 0.10), tx("expense", 0.20)])
        assert result["total_expenses"] == 0.30


class TestLargestExpense:
    async def test_is_the_biggest_expense(self, mock_db):
        result = await report(mock_db, [
            tx("expense", 20, description="Lunch"),
            tx("expense", 950, description="Rent"),
            tx("expense", 60, description="Fuel"),
        ])
        assert result["largest_expense"] == {"description": "Rent", "amount": 950}

    async def test_ignores_income_even_if_larger(self, mock_db):
        result = await report(mock_db, [tx("income", 5000, description="Salary"), tx("expense", 30, description="Lunch")])
        assert result["largest_expense"] == {"description": "Lunch", "amount": 30}

    async def test_tie_keeps_the_first_one(self, mock_db):
        result = await report(mock_db, [tx("expense", 50, description="First"), tx("expense", 50, description="Second")])
        assert result["largest_expense"]["description"] == "First"

    async def test_is_none_when_there_are_only_incomes(self, mock_db):
        result = await report(mock_db, [tx("income", 100)])
        assert result["largest_expense"] is None


class TestTopSpendingCategory:
    async def test_is_the_category_with_the_highest_total_not_the_biggest_single_expense(self, mock_db):
        mock_db.categories.find_one.return_value = {"_id": FOOD, "name": "Food"}
        result = await report(mock_db, [
            tx("expense", 40, FOOD), tx("expense", 40, FOOD), tx("expense", 40, FOOD),
            tx("expense", 100, RENT),
        ])
        assert result["top_spending_category"] == "Food"
        mock_db.categories.find_one.assert_awaited_once_with({"_id": FOOD})

    async def test_income_categories_do_not_count(self, mock_db):
        mock_db.categories.find_one.return_value = {"_id": RENT, "name": "Rent"}
        await report(mock_db, [tx("income", 5000, FOOD), tx("expense", 10, RENT)])
        mock_db.categories.find_one.assert_awaited_once_with({"_id": RENT})

    async def test_deleted_category_gives_n_a(self, mock_db):
        mock_db.categories.find_one.return_value = None
        result = await report(mock_db, [tx("expense", 10, FOOD)])
        assert result["top_spending_category"] == "N/A"

    async def test_malformed_category_id_gives_n_a(self, mock_db):
        bad = tx("expense", 10)
        bad["category_id"] = "not-an-object-id"
        result = await report(mock_db, [bad])
        assert result["top_spending_category"] == "N/A"
        mock_db.categories.find_one.assert_not_awaited()

    async def test_expenses_without_a_category_field_count_as_uncategorised(self, mock_db):
        no_field = tx("expense", 60)
        del no_field["category_id"]
        mock_db.categories.find_one.return_value = {"_id": FOOD, "name": "Food"}
        result = await report(mock_db, [no_field, tx("expense", 50), tx("expense", 100, FOOD)])
        assert result["top_spending_category"] == "N/A"
        mock_db.categories.find_one.assert_not_awaited()

    async def test_uncategorised_expenses_give_n_a_without_a_lookup(self, mock_db):
        result = await report(mock_db, [tx("expense", 10)])
        assert result["top_spending_category"] == "N/A"
        mock_db.categories.find_one.assert_not_awaited()


class TestTransactionsPassthrough:
    async def test_raw_transactions_are_returned_for_the_csv_export(self, mock_db):
        transactions = [tx("income", 1), tx("expense", 2)]
        result = await report(mock_db, transactions)
        assert result["transactions"] is transactions
