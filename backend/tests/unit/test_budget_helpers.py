
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.routers.budgets import compute_spent, enrich_budget

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]

CATEGORY_ID = ObjectId()


def make_budget(**overrides) -> dict:
    budget = {
        "_id": ObjectId(),
        "category_id": str(CATEGORY_ID),
        "month_year": "2026-01",
        "limit_amount": 100.0,
        "spent_amount": 0.0,
    }
    budget.update(overrides)
    return budget


class TestPercentageBoundaries:

    @pytest.mark.parametrize(
        "spent, limit, expected",
        [
            (0, 100, 0),
            (0.01, 100, 0.01),
            (79.99, 100, 79.99),
            (80, 100, 80),
            (80.01, 100, 80.01),
            (99.99, 100, 99.99),
            (100, 100, 100),
            (0.01, 0.01, 100),
            (250, 1000, 25),
        ],
        ids=["0%", "0.01%", "79.99%", "80%", "80.01%", "99.99%", "100%", "tiny-limit", "25%"],
    )
    async def test_percentage_is_spent_over_limit(self, mock_db, spent, limit, expected):
        result = await enrich_budget(make_budget(spent_amount=spent, limit_amount=limit), mock_db)
        assert result["percentage"] == pytest.approx(expected)

    @pytest.mark.parametrize(
        "spent", [100.01, 150, 1_000_000], ids=["just-over", "150%", "far-over"]
    )
    async def test_percentage_is_capped_at_100_when_over_budget(self, mock_db, spent):
        result = await enrich_budget(make_budget(spent_amount=spent, limit_amount=100), mock_db)
        assert result["percentage"] == 100

    async def test_over_budget_amounts_are_still_reported_uncapped(self, mock_db):
        result = await enrich_budget(make_budget(spent_amount=150, limit_amount=100), mock_db)
        assert result["spent_amount"] == 150
        assert result["limit_amount"] == 100


class TestLimitGuard:

    @pytest.mark.parametrize("limit", [0, -0.01, -100], ids=["zero", "just-negative", "negative"])
    async def test_non_positive_limit_gives_zero_percent(self, mock_db, limit):
        result = await enrich_budget(make_budget(spent_amount=50, limit_amount=limit), mock_db)
        assert result["percentage"] == 0


class TestDefaults:
    async def test_missing_spent_amount_counts_as_zero(self, mock_db):
        budget = make_budget(limit_amount=100)
        del budget["spent_amount"]
        result = await enrich_budget(budget, mock_db)
        assert result["spent_amount"] == 0
        assert result["percentage"] == 0

    async def test_missing_limit_amount_defaults_to_one(self, mock_db):
        budget = make_budget(spent_amount=0.5)
        del budget["limit_amount"]
        result = await enrich_budget(budget, mock_db)
        assert result["limit_amount"] == 1
        assert result["percentage"] == pytest.approx(50)


class TestCategoryResolution:
    async def test_uses_the_categorys_name_and_icon(self, mock_db):
        mock_db.categories.find_one.return_value = {"_id": CATEGORY_ID, "name": "Food", "icon": "utensils"}
        result = await enrich_budget(make_budget(), mock_db)
        assert result["category_name"] == "Food"
        assert result["category_icon"] == "utensils"
        mock_db.categories.find_one.assert_awaited_once_with({"_id": CATEGORY_ID})

    async def test_icon_defaults_to_tag_when_category_has_none(self, mock_db):
        mock_db.categories.find_one.return_value = {"_id": CATEGORY_ID, "name": "Food"}
        result = await enrich_budget(make_budget(), mock_db)
        assert result["category_icon"] == "tag"

    async def test_missing_category_falls_back_to_unknown(self, mock_db):
        mock_db.categories.find_one.return_value = None
        result = await enrich_budget(make_budget(), mock_db)
        assert result["category_name"] == "Unknown"
        assert result["category_icon"] == "tag"

    async def test_empty_category_id_skips_the_lookup(self, mock_db):
        result = await enrich_budget(make_budget(category_id=""), mock_db)
        assert result["category_name"] == "Unknown"
        mock_db.categories.find_one.assert_not_awaited()


class TestFieldMapping:
    async def test_maps_all_output_fields(self, mock_db):
        budget = make_budget(spent_amount=25, limit_amount=50, month_year="2026-12")
        result = await enrich_budget(budget, mock_db)
        assert result == {
            "id": str(budget["_id"]),
            "category_id": str(CATEGORY_ID),
            "category_name": "Unknown",
            "category_icon": "tag",
            "month_year": "2026-12",
            "limit_amount": 50,
            "spent_amount": 25,
            "percentage": 50,
        }


def aggregation_returns(mock_db, rows: list) -> MagicMock:
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=rows)
    mock_db.transactions.aggregate = MagicMock(return_value=cursor)
    return mock_db.transactions.aggregate


def match_stage(aggregate: MagicMock) -> dict:
    pipeline = aggregate.call_args.args[0]
    return pipeline[0]["$match"]


class TestComputeSpentMonthWindow:
    @pytest.mark.parametrize(
        "month_year, start, end",
        [
            ("2026-01", datetime(2026, 1, 1), datetime(2026, 2, 1)),
            ("2026-11", datetime(2026, 11, 1), datetime(2026, 12, 1)),
            ("2026-12", datetime(2026, 12, 1), datetime(2027, 1, 1)),
            ("2026-02", datetime(2026, 2, 1), datetime(2026, 3, 1)),
            ("2028-02", datetime(2028, 2, 1), datetime(2028, 3, 1)),
            ("1999-12", datetime(1999, 12, 1), datetime(2000, 1, 1)),
        ],
        ids=["jan", "nov", "dec->next-year", "feb", "leap-feb", "century"],
    )
    async def test_window_covers_exactly_one_calendar_month(self, mock_db, month_year, start, end):
        aggregate = aggregation_returns(mock_db, [])
        await compute_spent(mock_db, "user-1", "cat-1", month_year)
        assert match_stage(aggregate)["date"] == {"$gte": start, "$lt": end}

    async def test_window_end_is_exclusive(self, mock_db):
        aggregate = aggregation_returns(mock_db, [])
        await compute_spent(mock_db, "user-1", "cat-1", "2026-01")
        assert "$lte" not in match_stage(aggregate)["date"]

    async def test_month_without_leading_zero_gives_the_same_window(self, mock_db):
        aggregate = aggregation_returns(mock_db, [])
        await compute_spent(mock_db, "user-1", "cat-1", "2026-1")
        assert match_stage(aggregate)["date"] == {"$gte": datetime(2026, 1, 1), "$lt": datetime(2026, 2, 1)}

    @pytest.mark.parametrize("month_year", ["2026-00", "2026-13", "abc", ""], ids=["month-0", "month-13", "text", "empty"])
    async def test_invalid_month_year_raises_value_error(self, mock_db, month_year):
        aggregation_returns(mock_db, [])
        with pytest.raises(ValueError):
            await compute_spent(mock_db, "user-1", "cat-1", month_year)


class TestComputeSpentFilterAndResult:
    async def test_only_this_users_expenses_in_this_category_are_summed(self, mock_db):
        aggregate = aggregation_returns(mock_db, [])
        await compute_spent(mock_db, "user-1", "cat-1", "2026-01")
        match = match_stage(aggregate)
        assert match["user_id"] == "user-1"
        assert match["category_id"] == "cat-1"
        assert match["type"] == "expense"

    async def test_amounts_are_summed_in_a_single_group(self, mock_db):
        aggregate = aggregation_returns(mock_db, [])
        await compute_spent(mock_db, "user-1", "cat-1", "2026-01")
        pipeline = aggregate.call_args.args[0]
        assert pipeline[1] == {"$group": {"_id": None, "total": {"$sum": "$amount"}}}

    async def test_returns_the_aggregated_total(self, mock_db):
        aggregation_returns(mock_db, [{"_id": None, "total": 123.45}])
        assert await compute_spent(mock_db, "user-1", "cat-1", "2026-01") == 123.45

    async def test_returns_zero_when_nothing_matches(self, mock_db):
        aggregation_returns(mock_db, [])
        result = await compute_spent(mock_db, "user-1", "cat-1", "2026-01")
        assert result == 0.0
        assert isinstance(result, float)
