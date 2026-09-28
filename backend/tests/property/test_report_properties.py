
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from hypothesis import given
from hypothesis import strategies as st

from app.routers.reports import get_report_data

pytestmark = pytest.mark.property

CATEGORIES = {ObjectId(): name for name in ["Food", "Rent", "Travel"]}
CATEGORY_IDS = list(CATEGORIES)

money = st.integers(min_value=1, max_value=1_000_000_000).map(lambda cents: cents / 100)


def close(a: float, b: float) -> bool:
    return a == pytest.approx(b, rel=1e-9, abs=1e-6)


@st.composite
def transactions(draw, type_=None):
    category = draw(st.sampled_from(CATEGORY_IDS))
    return {
        "_id": ObjectId(),
        "type": type_ or draw(st.sampled_from(["income", "expense"])),
        "amount": draw(money),
        "category_id": str(category),
        "description": draw(st.text(max_size=20)),
    }


months = st.lists(transactions(), max_size=40)
incomes = transactions(type_="income")
expenses = transactions(type_="expense")


async def report(txs: list) -> dict:
    """Run get_report_data against a mocked database holding `txs`."""
    db = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=txs)
    db.transactions.find = MagicMock(return_value=cursor)

    async def find_category(query):
        return {"_id": query["_id"], "name": CATEGORIES[query["_id"]]}

    db.categories.find_one = AsyncMock(side_effect=find_category)
    return await get_report_data(db, "user-1", "2026-01")


def expense_totals_by_category(txs: list) -> dict:
    totals = {}
    for t in txs:
        if t["type"] == "expense":
            totals[t["category_id"]] = totals.get(t["category_id"], 0) + t["amount"]
    return totals


@given(months)
async def test_savings_is_income_minus_expenses(txs):
    r = await report(txs)
    assert r["savings"] == r["total_income"] - r["total_expenses"]
    assert r["total_income"] >= 0 and r["total_expenses"] >= 0


@given(months)
async def test_savings_rate_is_consistent_and_never_above_100(txs):
    r = await report(txs)
    assert r["savings_rate"] <= 100 + 1e-9
    if r["total_income"] > 0:
        assert close(r["savings_rate"] * r["total_income"] / 100, r["savings"])
    else:
        assert r["savings_rate"] == 0


@given(months)
async def test_largest_expense_is_the_maximum_expense(txs):
    r = await report(txs)
    expense_amounts = [t["amount"] for t in txs if t["type"] == "expense"]
    if not expense_amounts:
        assert r["largest_expense"] is None
    else:
        assert r["largest_expense"]["amount"] == max(expense_amounts)
        assert r["largest_expense"]["description"] in [t["description"] for t in txs if t["type"] == "expense"]


@given(months)
async def test_top_category_has_the_highest_expense_total(txs):
    r = await report(txs)
    totals = expense_totals_by_category(txs)
    if not totals:
        assert r["top_spending_category"] == "N/A"
    else:
        best = max(totals.values())
        winners = {CATEGORIES[ObjectId(cid)] for cid, total in totals.items() if total == best}
        assert r["top_spending_category"] in winners


@given(months, st.randoms(use_true_random=False))
async def test_order_of_transactions_does_not_matter(txs, rnd):
    shuffled = txs[:]
    rnd.shuffle(shuffled)
    a, b = await report(txs), await report(shuffled)
    assert close(a["total_income"], b["total_income"])
    assert close(a["total_expenses"], b["total_expenses"])
    assert (a["largest_expense"] or {}).get("amount") == (b["largest_expense"] or {}).get("amount")


@given(months, incomes)
async def test_adding_an_income_only_moves_the_income_side(txs, extra):
    before, after = await report(txs), await report(txs + [extra])
    assert close(after["total_income"], before["total_income"] + extra["amount"])
    assert after["total_expenses"] == before["total_expenses"]
    assert after["largest_expense"] == before["largest_expense"]


@given(months, expenses)
async def test_adding_an_expense_moves_totals_and_can_only_raise_the_largest(txs, extra):
    before, after = await report(txs), await report(txs + [extra])
    assert close(after["total_expenses"], before["total_expenses"] + extra["amount"])
    assert after["total_income"] == before["total_income"]
    previous_max = (before["largest_expense"] or {"amount": 0})["amount"]
    assert after["largest_expense"]["amount"] == max(previous_max, extra["amount"])


@given(months, expenses)
async def test_splitting_an_expense_in_two_keeps_every_total(txs, expense):
    half = expense["amount"] / 2
    split = [dict(expense, _id=ObjectId(), amount=half), dict(expense, _id=ObjectId(), amount=expense["amount"] - half)]
    whole, parts = await report(txs + [expense]), await report(txs + split)
    assert close(whole["total_expenses"], parts["total_expenses"])
    assert close(whole["savings"], parts["savings"])
    assert close(whole["total_income"], parts["total_income"])
