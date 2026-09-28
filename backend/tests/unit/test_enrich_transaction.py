
import pytest
from datetime import datetime
from bson import ObjectId

from app.routers.transactions import enrich_transaction

pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]


def make_tx(**overrides) -> dict:
    tx = {
        "_id": ObjectId(),
        "type": "expense",
        "amount": 42.5,
        "date": datetime(2026, 1, 15),
        "category_id": str(ObjectId()),
        "description": "Coffee",
        "payment_method": "Credit Card",
        "merchant": "Blue Bottle",
        "notes": "with a friend",
        "is_recurring": False,
        "recurrence_rule": None,
    }
    tx.update(overrides)
    return tx


class TestEnrichTransactionWithExistingCategory:
    async def test_resolves_category_name_from_db(self, mock_db):
        category_id = str(ObjectId())
        tx = make_tx(category_id=category_id)
        mock_db.categories.find_one.return_value = {"_id": ObjectId(category_id), "name": "Food & Dining"}

        result = await enrich_transaction(tx, mock_db)

        assert result["category_name"] == "Food & Dining"
        mock_db.categories.find_one.assert_awaited_once()

    async def test_looks_up_category_by_the_transactions_category_id(self, mock_db):
        category_id = str(ObjectId())
        tx = make_tx(category_id=category_id)
        mock_db.categories.find_one.return_value = {"_id": ObjectId(category_id), "name": "Transport"}

        await enrich_transaction(tx, mock_db)

        called_filter = mock_db.categories.find_one.call_args.args[0]
        assert called_filter == {"_id": ObjectId(category_id)}


class TestEnrichTransactionWithMissingCategory:
    async def test_falls_back_to_unknown_when_category_not_found(self, mock_db):
        tx = make_tx(category_id=str(ObjectId()))
        mock_db.categories.find_one.return_value = None

        result = await enrich_transaction(tx, mock_db)

        assert result["category_name"] == "Unknown"

    async def test_does_not_query_db_when_category_id_missing(self, mock_db):
        tx = make_tx(category_id=None)
        del tx["category_id"]

        result = await enrich_transaction(tx, mock_db)

        assert result["category_name"] == "Unknown"
        assert result["category_id"] == ""
        mock_db.categories.find_one.assert_not_awaited()

    async def test_empty_string_category_id_is_treated_as_missing(self, mock_db):
        tx = make_tx(category_id="")

        result = await enrich_transaction(tx, mock_db)

        assert result["category_name"] == "Unknown"
        mock_db.categories.find_one.assert_not_awaited()


class TestEnrichTransactionFieldMapping:
    async def test_maps_all_expected_output_fields(self, mock_db):
        tx = make_tx()
        mock_db.categories.find_one.return_value = {"name": "Housing"}

        result = await enrich_transaction(tx, mock_db)

        assert result["id"] == str(tx["_id"])
        assert result["type"] == tx["type"]
        assert result["amount"] == tx["amount"]
        assert result["date"] == tx["date"]
        assert result["description"] == tx["description"]
        assert result["payment_method"] == tx["payment_method"]
        assert result["merchant"] == tx["merchant"]
        assert result["notes"] == tx["notes"]
        assert result["is_recurring"] == tx["is_recurring"]
        assert result["recurrence_rule"] == tx["recurrence_rule"]

    async def test_id_is_stringified_not_an_objectid(self, mock_db):
        tx = make_tx()
        result = await enrich_transaction(tx, mock_db)
        assert isinstance(result["id"], str)
        assert result["id"] == str(tx["_id"])

    @pytest.mark.parametrize("tx_type", ["income", "expense"])
    async def test_handles_both_transaction_types(self, mock_db, tx_type):
        tx = make_tx(type=tx_type)
        result = await enrich_transaction(tx, mock_db)
        assert result["type"] == tx_type

    async def test_defaults_is_recurring_to_false_when_absent(self, mock_db):
        tx = make_tx()
        del tx["is_recurring"]

        result = await enrich_transaction(tx, mock_db)

        assert result["is_recurring"] is False

    async def test_optional_fields_default_to_none_when_absent(self, mock_db):
        tx = make_tx()
        for optional_field in ("payment_method", "merchant", "notes", "recurrence_rule"):
            del tx[optional_field]

        result = await enrich_transaction(tx, mock_db)

        assert result["payment_method"] is None
        assert result["merchant"] is None
        assert result["notes"] is None
        assert result["recurrence_rule"] is None

    async def test_recurring_transaction_keeps_its_recurrence_rule(self, mock_db):
        tx = make_tx(is_recurring=True, recurrence_rule="monthly")
        result = await enrich_transaction(tx, mock_db)
        assert result["is_recurring"] is True
        assert result["recurrence_rule"] == "monthly"

    @pytest.mark.parametrize("amount", [0.01, 1, 42.5, 9999.99])
    async def test_preserves_various_amounts_exactly(self, mock_db, amount):
        tx = make_tx(amount=amount)
        result = await enrich_transaction(tx, mock_db)
        assert result["amount"] == amount
