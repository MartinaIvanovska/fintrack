
import calendar
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from hypothesis import assume, event, given
from hypothesis import strategies as st

from app.routers.budgets import compute_spent, enrich_budget
from app.routers.reports import get_report_data

pytestmark = pytest.mark.property

years = st.integers(min_value=1900, max_value=2200)
months = st.integers(min_value=1, max_value=12)
cents = st.integers(min_value=1, max_value=1_000_000_000)


def fake_db():
    db = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    db.transactions.aggregate = MagicMock(return_value=cursor)
    db.transactions.find = MagicMock(return_value=cursor)
    db.categories.find_one = AsyncMock(return_value=None)
    return db


async def budget_window(month_year: str) -> tuple:
    db = fake_db()
    await compute_spent(db, "user-1", "cat-1", month_year)
    date_filter = db.transactions.aggregate.call_args.args[0][0]["$match"]["date"]
    return date_filter["$gte"], date_filter["$lt"]


async def report_window(month_year: str) -> tuple:
    db = fake_db()
    await get_report_data(db, "user-1", month_year)
    date_filter = db.transactions.find.call_args.args[0]["date"]
    return date_filter["$gte"], date_filter["$lt"]


@given(years, months)
async def test_window_is_exactly_one_calendar_month(year, month):
    start, end = await budget_window(f"{year}-{month:02d}")
    assert start == datetime(year, month, 1)
    assert end.day == 1 and end > start
    assert (end - start).days == calendar.monthrange(year, month)[1]


@given(
    years, months,
    st.integers(min_value=-40 * 86400, max_value=40 * 86400),
    st.booleans(),
)
async def test_a_moment_is_inside_the_window_iff_it_is_in_that_month(year, month, offset_seconds, whole_days):
    if whole_days:
        offset_seconds -= offset_seconds % 86400
    moment = datetime(year, month, 1) + timedelta(seconds=offset_seconds)
    start, end = await budget_window(f"{year}-{month:02d}")
    inside = start <= moment < end
    event("inside" if inside else "outside")
    if moment in (start, end):
        event("exactly on a boundary")
    assert inside == ((moment.year, moment.month) == (year, month))


@given(years, months)
async def test_consecutive_months_tile_without_gaps_or_overlap(year, month):
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)
    assume(next_year <= 2200)
    _, end = await budget_window(f"{year}-{month:02d}")
    next_start, _ = await budget_window(f"{next_year}-{next_month:02d}")
    assert end == next_start


@given(years, months)
async def test_budgets_and_reports_use_the_same_window(year, month):
    month_year = f"{year}-{month:02d}"
    assert await budget_window(month_year) == await report_window(month_year)


@given(years, months)
async def test_leading_zero_on_the_month_is_optional(year, month):
    assert await budget_window(f"{year}-{month}") == await budget_window(f"{year}-{month:02d}")


@given(years, st.one_of(st.integers(max_value=0), st.integers(min_value=13, max_value=99)))
async def test_months_outside_1_to_12_are_rejected(year, month):
    with pytest.raises(ValueError):
        await budget_window(f"{year}-{month:02d}")


async def percentage(spent: float, limit: float) -> float:
    budget = {"_id": ObjectId(), "category_id": "", "month_year": "2026-01",
              "spent_amount": spent, "limit_amount": limit}
    return (await enrich_budget(budget, fake_db()))["percentage"]


@given(st.integers(min_value=0, max_value=10**10), cents)
async def test_percentage_stays_between_0_and_100(spent_cents, limit_cents):
    p = await percentage(spent_cents / 100, limit_cents / 100)
    assert 0 <= p <= 100


@given(st.integers(min_value=0, max_value=10**10), cents)
async def test_percentage_is_100_exactly_when_spending_reaches_the_limit(spent_cents, limit_cents):
    p = await percentage(spent_cents / 100, limit_cents / 100)
    assert (p == 100) == (spent_cents >= limit_cents)


@given(st.integers(min_value=0, max_value=10**10), st.integers(min_value=0, max_value=10**10), cents)
async def test_spending_more_never_lowers_the_percentage(a, b, limit_cents):
    low, high = sorted((a, b))
    assert await percentage(low / 100, limit_cents / 100) <= await percentage(high / 100, limit_cents / 100)


@given(st.integers(min_value=0, max_value=10**8), cents, st.integers(min_value=2, max_value=1000))
async def test_scaling_spent_and_limit_together_keeps_the_percentage(spent_cents, limit_cents, k):
    p = await percentage(spent_cents / 100, limit_cents / 100)
    scaled = await percentage(spent_cents * k / 100, limit_cents * k / 100)
    assert scaled == pytest.approx(p, rel=1e-9, abs=1e-9)


@given(st.floats(min_value=0, max_value=1e9, allow_nan=False),
       st.floats(max_value=0, allow_nan=False, allow_infinity=False))
async def test_non_positive_limit_always_gives_zero(spent, limit):
    assert await percentage(spent, limit) == 0
