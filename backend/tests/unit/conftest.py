
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.categories = MagicMock()
    db.categories.find_one = AsyncMock(return_value=None)
    db.users = MagicMock()
    db.users.find_one = AsyncMock(return_value=None)
    db.transactions = MagicMock()
    db.transactions.find_one = AsyncMock(return_value=None)
    db.transactions.insert_one = AsyncMock()
    db.transactions.update_one = AsyncMock()
    db.transactions.delete_one = AsyncMock()
    db.transactions.count_documents = AsyncMock(return_value=0)
    return db
