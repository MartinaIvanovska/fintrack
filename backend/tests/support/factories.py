
import itertools
from datetime import datetime
from functools import lru_cache

from faker import Faker

from app.core.security import get_password_hash

DEFAULT_PASSWORD = "password123"

_fake = Faker()
_fake.seed_instance(1234)
_sequence = itertools.count(1)


@lru_cache(maxsize=None)
def _password_hash(password: str) -> str:
    return get_password_hash(password)


class Factory:
    def __init__(self, db):
        self.db = db

    async def _insert(self, collection: str, doc: dict) -> dict:
        result = await self.db[collection].insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    async def user(self, password: str = DEFAULT_PASSWORD, **overrides) -> dict:
        n = next(_sequence)
        doc = {
            "username": f"user{n}",
            "email": f"user{n}@example.com",
            "hashed_password": _password_hash(password),
            "created_at": datetime(2026, 1, 1),
        }
        doc.update(overrides)
        return await self._insert("users", doc)

    async def category(self, user: dict, **overrides) -> dict:
        doc = {
            "name": _fake.unique.word().title(),
            "type": "expense",
            "icon": "tag",
            "user_id": str(user["_id"]),
            "is_default": False,
            "created_at": datetime(2026, 1, 1),
        }
        doc.update(overrides)
        return await self._insert("categories", doc)

    async def transaction(self, user: dict, category: dict = None, **overrides) -> dict:
        doc = {
            "type": category["type"] if category else "expense",
            "amount": 10.0,
            "date": datetime(2026, 1, 15),
            "category_id": str(category["_id"]) if category else "",
            "description": _fake.sentence(nb_words=3).rstrip("."),
            "payment_method": None,
            "merchant": _fake.company(),
            "notes": None,
            "is_recurring": False,
            "recurrence_rule": None,
            "user_id": str(user["_id"]),
            "created_at": datetime(2026, 1, 15),
        }
        doc.update(overrides)
        return await self._insert("transactions", doc)

    async def budget(self, user: dict, category: dict, **overrides) -> dict:
        doc = {
            "category_id": str(category["_id"]),
            "month_year": "2026-01",
            "limit_amount": 100.0,
            "spent_amount": 0.0,
            "user_id": str(user["_id"]),
            "created_at": datetime(2026, 1, 1),
        }
        doc.update(overrides)
        return await self._insert("budgets", doc)
