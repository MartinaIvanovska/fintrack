
from datetime import datetime, timezone

import pytest
import time_machine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


def frozen_at(*args):
    return time_machine.travel(datetime(*args, tzinfo=timezone.utc), tick=False)


async def dashboard(client) -> dict:
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def food(make, test_user):
    return await make.category(test_user, name="Food", icon="utensils")


@pytest.fixture
async def salary(make, test_user):
    return await make.category(test_user, name="Salary", type="income", icon="briefcase")


class TestCurrentMonthTotals:
    async def test_empty_account(self, client):
        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["total_income"] == 0
        assert d["total_expenses"] == 0
        assert d["remaining_balance"] == 0
        assert d["savings_rate"] == 0
        assert d["spending_by_category"] == []
        assert d["recent_transactions"] == []
        assert [m["month"] for m in d["monthly_trend"]] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        assert all(m["expenses"] == 0 for m in d["monthly_trend"])

    @pytest.mark.parametrize(
        "date, counts",
        [
            (datetime(2026, 5, 31, 23, 59, 59), False),
            (datetime(2026, 6, 1, 0, 0, 0), True),
            (datetime(2026, 6, 30, 23, 59, 59), True),
            (datetime(2026, 7, 1, 0, 0, 0), False),
        ],
        ids=["may-31-23:59:59", "jun-1-00:00", "jun-30-23:59:59", "jul-1-00:00"],
    )
    async def test_only_the_current_month_counts(self, client, make, test_user, food, date, counts):
        await make.transaction(test_user, food, amount=40, date=date)

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["total_expenses"] == (40 if counts else 0)

    async def test_balance_and_savings_rate(self, client, make, test_user, food, salary):
        await make.transaction(test_user, salary, amount=2000, date=datetime(2026, 6, 1))
        await make.transaction(test_user, food, amount=500, date=datetime(2026, 6, 10))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["total_income"] == 2000
        assert d["total_expenses"] == 500
        assert d["remaining_balance"] == 1500
        assert d["savings_rate"] == 75

    async def test_overspending_gives_a_negative_balance_and_rate(self, client, make, test_user, food, salary):
        await make.transaction(test_user, salary, amount=1000, date=datetime(2026, 6, 1))
        await make.transaction(test_user, food, amount=1500, date=datetime(2026, 6, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["remaining_balance"] == -500
        assert d["savings_rate"] == -50

    async def test_no_income_gives_zero_savings_rate(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=80, date=datetime(2026, 6, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["remaining_balance"] == -80
        assert d["savings_rate"] == 0

    async def test_other_users_transactions_are_not_included(self, client, make, other_user):
        cat = await make.category(other_user)
        await make.transaction(other_user, cat, amount=999, date=datetime(2026, 6, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["total_expenses"] == 0
        assert d["recent_transactions"] == []


class TestYearBoundaries:
    async def test_last_second_of_december(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=10, date=datetime(2026, 12, 31, 23, 0))
        await make.transaction(test_user, food, amount=99, date=datetime(2027, 1, 1, 0, 0))

        with frozen_at(2026, 12, 31, 23, 59, 59):
            d = await dashboard(client)

        assert d["total_expenses"] == 10
        assert [m["month"] for m in d["monthly_trend"]] == ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        assert d["monthly_trend"][-1]["expenses"] == 10

    async def test_first_second_of_january(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=10, date=datetime(2025, 12, 31, 23, 59, 59))
        await make.transaction(test_user, food, amount=7, date=datetime(2026, 1, 1, 0, 0, 0))

        with frozen_at(2026, 1, 1, 0, 0, 0):
            d = await dashboard(client)

        assert d["total_expenses"] == 7
        assert [m["month"] for m in d["monthly_trend"]] == ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan"]
        assert [m["expenses"] for m in d["monthly_trend"]][-2:] == [10, 7]


class TestSixMonthTrend:
    async def test_trend_crosses_into_the_previous_year(self, client, make, test_user, food, salary):
        await make.transaction(test_user, food, amount=300, date=datetime(2025, 10, 15))
        await make.transaction(test_user, salary, amount=1000, date=datetime(2025, 10, 1))
        await make.transaction(test_user, food, amount=50, date=datetime(2026, 2, 3))

        with frozen_at(2026, 2, 10, 9):
            d = await dashboard(client)

        trend = {m["month"]: m for m in d["income_vs_expenses"]}
        assert list(trend) == ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb"]
        assert trend["Oct"] == {"month": "Oct", "income": 1000, "expenses": 300, "savings": 700}
        assert trend["Feb"]["expenses"] == 50
        assert [m["expenses"] for m in d["monthly_trend"]] == [0, 300, 0, 0, 0, 50]

    async def test_savings_in_the_trend_never_go_below_zero(self, client, make, test_user, food, salary):
        await make.transaction(test_user, salary, amount=100, date=datetime(2026, 5, 1))
        await make.transaction(test_user, food, amount=400, date=datetime(2026, 5, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        may = next(m for m in d["income_vs_expenses"] if m["month"] == "May")
        assert may["savings"] == 0

    async def test_data_older_than_six_months_is_left_out(self, client, make, test_user, food):
        await make.transaction(test_user, food, amount=123, date=datetime(2025, 12, 31, 23, 59, 59))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert all(m["expenses"] == 0 for m in d["monthly_trend"])


class TestSpendingByCategory:
    async def test_grouped_and_sorted_by_total(self, client, make, test_user, food, salary):
        rent = await make.category(test_user, name="Rent")
        await make.transaction(test_user, food, amount=30, date=datetime(2026, 6, 2))
        await make.transaction(test_user, food, amount=30, date=datetime(2026, 6, 3))
        await make.transaction(test_user, rent, amount=900, date=datetime(2026, 6, 1))
        await make.transaction(test_user, salary, amount=5000, date=datetime(2026, 6, 1))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["spending_by_category"] == [{"name": "Rent", "value": 900}, {"name": "Food", "value": 60}]

    async def test_uncategorised_spending_is_shown_as_other(self, client, make, test_user):
        await make.transaction(test_user, None, amount=15, date=datetime(2026, 6, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert d["spending_by_category"] == [{"name": "Other", "value": 15}]

    async def test_only_the_top_eight_categories_are_shown(self, client, make, test_user):
        for i in range(1, 10):
            cat = await make.category(test_user, name=f"C{i}")
            await make.transaction(test_user, cat, amount=i, date=datetime(2026, 6, 2))

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        assert [c["name"] for c in d["spending_by_category"]] == [f"C{i}" for i in range(9, 1, -1)]


class TestRecentTransactions:
    async def test_five_newest_across_months_newest_first(self, client, make, test_user, food):
        dates = [datetime(2026, 1, 5), datetime(2026, 3, 1), datetime(2026, 6, 10),
                 datetime(2026, 2, 14), datetime(2026, 5, 31), datetime(2026, 4, 4), datetime(2025, 12, 1)]
        for i, date in enumerate(dates):
            await make.transaction(test_user, food, amount=i + 1, date=date, description=f"tx{i}")

        with frozen_at(2026, 6, 15, 12):
            d = await dashboard(client)

        recent = d["recent_transactions"]
        assert [r["date"] for r in recent] == [
            "2026-06-10T00:00:00", "2026-05-31T00:00:00", "2026-04-04T00:00:00",
            "2026-03-01T00:00:00", "2026-02-14T00:00:00",
        ]

    async def test_fields_and_category_details(self, client, make, test_user, food):
        tx = await make.transaction(test_user, food, amount=12.5, date=datetime(2026, 6, 1), description="Lunch")

        with frozen_at(2026, 6, 15, 12):
            [recent] = (await dashboard(client))["recent_transactions"]

        assert recent == {
            "id": str(tx["_id"]), "description": "Lunch", "amount": 12.5, "type": "expense",
            "date": "2026-06-01T00:00:00", "category_name": "Food", "category_icon": "utensils",
        }

    async def test_missing_category_falls_back_to_other_and_tag(self, client, make, test_user):
        await make.transaction(test_user, None, date=datetime(2026, 6, 1))

        with frozen_at(2026, 6, 15, 12):
            [recent] = (await dashboard(client))["recent_transactions"]

        assert recent["category_name"] == "Other"
        assert recent["category_icon"] == "tag"


async def test_dashboard_requires_authentication(unauthenticated_client):
    assert (await unauthenticated_client.get("/api/dashboard")).status_code == 401
