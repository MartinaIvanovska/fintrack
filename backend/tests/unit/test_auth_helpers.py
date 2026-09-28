
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.routers.auth import seed_default_categories, user_to_out
from app.schemas.schemas import UserOut

pytestmark = pytest.mark.unit


def stored_user(**overrides) -> dict:
    user = {
        "_id": ObjectId(),
        "username": "martina",
        "email": "martina@example.com",
        "hashed_password": "$2b$12$not-a-real-hash",
        "created_at": datetime(2026, 1, 1, 12, 30),
    }
    user.update(overrides)
    return user


class TestUserToOut:
    def test_maps_the_public_fields(self):
        user = stored_user()
        out = user_to_out(user)
        assert isinstance(out, UserOut)
        assert out.model_dump() == {
            "id": str(user["_id"]),
            "username": "martina",
            "email": "martina@example.com",
            "created_at": datetime(2026, 1, 1, 12, 30),
        }

    def test_never_exposes_the_password_hash(self):
        dumped = user_to_out(stored_user()).model_dump_json()
        assert "hashed_password" not in dumped
        assert "$2b$" not in dumped

    def test_id_is_a_string(self):
        assert isinstance(user_to_out(stored_user()).id, str)

    def test_missing_created_at_defaults_to_now(self):
        user = stored_user()
        del user["created_at"]
        before = datetime.utcnow()
        out = user_to_out(user)
        after = datetime.utcnow()
        assert before <= out.created_at <= after

    @pytest.mark.parametrize("field", ["_id", "username", "email"])
    def test_required_fields_must_be_present(self, field):
        user = stored_user()
        del user[field]
        with pytest.raises(KeyError):
            user_to_out(user)


EXPECTED_INCOME = ["Salary", "Freelance", "Investment", "Other Income"]
EXPECTED_EXPENSE = [
    "Food & Dining", "Housing", "Transport", "Healthcare", "Entertainment",
    "Shopping", "Utilities", "Subscriptions", "Education", "Other",
]


@pytest.fixture
def categories_db():
    db = MagicMock()
    db.categories.insert_one = AsyncMock()
    return db


def inserted(db) -> list:
    return [call.args[0] for call in db.categories.insert_one.await_args_list]


@pytest.mark.asyncio
class TestSeedDefaultCategories:
    async def test_inserts_fourteen_categories(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        assert categories_db.categories.insert_one.await_count == 14

    async def test_income_and_expense_categories(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        docs = inserted(categories_db)
        assert [d["name"] for d in docs if d["type"] == "income"] == EXPECTED_INCOME
        assert [d["name"] for d in docs if d["type"] == "expense"] == EXPECTED_EXPENSE

    async def test_every_category_belongs_to_the_user_and_is_marked_default(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        for doc in inserted(categories_db):
            assert doc["user_id"] == "user-1"
            assert doc["is_default"] is True

    async def test_every_category_has_an_icon(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        assert all(doc["icon"] for doc in inserted(categories_db))

    async def test_names_are_unique(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        names = [doc["name"] for doc in inserted(categories_db)]
        assert len(names) == len(set(names))

    async def test_two_users_get_separate_documents(self, categories_db):
        await seed_default_categories(categories_db, "user-1")
        await seed_default_categories(categories_db, "user-2")
        docs = inserted(categories_db)
        first, second = docs[:14], docs[14:]
        assert all(d["user_id"] == "user-1" for d in first)
        assert all(d["user_id"] == "user-2" for d in second)
        assert not any(a is b for a, b in zip(first, second))
