
import pytest
from pymongo.errors import DuplicateKeyError

from tests.support.mongo_indexes import INDEXES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


def _key_of(index_info: dict) -> list:
    if "weights" in index_info:
        return [(field, "text") for field in index_info["weights"]]
    return [(field, direction) for field, direction in index_info["key"]]


@pytest.mark.parametrize("collection, keys, options", INDEXES)
async def test_production_index_exists(db, collection, keys, options):
    info = await db[collection].index_information()
    matching = [i for i in info.values() if sorted(_key_of(i)) == sorted(keys)]
    assert matching, f"no index on {collection} with keys {keys}"
    assert matching[0].get("unique", False) == options.get("unique", False)


async def test_unique_email_is_enforced(db):
    await db.users.insert_one({"username": "a", "email": "same@example.com"})
    with pytest.raises(DuplicateKeyError):
        await db.users.insert_one({"username": "b", "email": "same@example.com"})


async def test_one_budget_per_category_and_month_is_enforced(db):
    budget = {"user_id": "u1", "category_id": "c1", "month_year": "2026-01", "limit_amount": 100}
    await db.budgets.insert_one(dict(budget))
    with pytest.raises(DuplicateKeyError):
        await db.budgets.insert_one(dict(budget))
