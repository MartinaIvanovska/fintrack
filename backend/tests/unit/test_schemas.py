
import pytest
from pydantic import ValidationError

from app.schemas.schemas import (
    TransactionCreate,
    TransactionUpdate,
    UserRegister,
    BudgetCreate,
)

pytestmark = [
    pytest.mark.unit,
]


VALID_TX_KWARGS = dict(
    type="expense",
    amount=10.0,
    date="2026-01-15T00:00:00",
    category_id="abc123",
    description="Groceries",
)


class TestTransactionCreateValidation:
    def test_valid_payload_parses_successfully(self):
        tx = TransactionCreate(**VALID_TX_KWARGS)
        assert tx.amount == 10.0
        assert tx.type == "expense"

    @pytest.mark.parametrize("bad_amount", [0, -1, -0.01])
    def test_non_positive_amount_is_rejected(self, bad_amount):
        with pytest.raises(ValidationError):
            TransactionCreate(**{**VALID_TX_KWARGS, "amount": bad_amount})

    def test_invalid_type_is_rejected(self):
        with pytest.raises(ValidationError):
            TransactionCreate(**{**VALID_TX_KWARGS, "type": "not-a-real-type"})

    @pytest.mark.parametrize("missing_field", ["type", "amount", "date", "category_id", "description"])
    def test_missing_required_field_is_rejected(self, missing_field):
        kwargs = {k: v for k, v in VALID_TX_KWARGS.items() if k != missing_field}
        with pytest.raises(ValidationError):
            TransactionCreate(**kwargs)

    def test_is_recurring_defaults_to_false(self):
        tx = TransactionCreate(**VALID_TX_KWARGS)
        assert tx.is_recurring is False

    def test_optional_fields_default_to_none(self):
        tx = TransactionCreate(**VALID_TX_KWARGS)
        assert tx.payment_method is None
        assert tx.merchant is None
        assert tx.notes is None
        assert tx.recurrence_rule is None


class TestTransactionUpdateValidation:
    def test_all_fields_optional_empty_payload_is_valid(self):
        update = TransactionUpdate()
        assert update.amount is None
        assert update.description is None

    def test_partial_update_only_sets_provided_fields(self):
        update = TransactionUpdate(description="New description")
        assert update.description == "New description"
        assert update.amount is None

    @pytest.mark.parametrize("bad_amount", [0, -5])
    def test_non_positive_amount_rejected_when_provided(self, bad_amount):
        with pytest.raises(ValidationError):
            TransactionUpdate(amount=bad_amount)


class TestUserRegisterValidation:
    def test_valid_registration_payload(self):
        user = UserRegister(username="jdoe", email="jdoe@example.com", password="hunter2")
        assert user.email == "jdoe@example.com"

    def test_invalid_email_is_rejected(self):
        with pytest.raises(ValidationError):
            UserRegister(username="jdoe", email="not-an-email", password="hunter2")

    @pytest.mark.parametrize("missing_field", ["username", "email", "password"])
    def test_missing_required_field_is_rejected(self, missing_field):
        kwargs = {"username": "jdoe", "email": "jdoe@example.com", "password": "hunter2"}
        del kwargs[missing_field]
        with pytest.raises(ValidationError):
            UserRegister(**kwargs)


class TestBudgetCreateValidation:
    def test_valid_budget_payload(self):
        budget = BudgetCreate(category_id="abc", month_year="2026-01", limit_amount=500)
        assert budget.limit_amount == 500

    @pytest.mark.parametrize("bad_limit", [0, -100])
    def test_non_positive_limit_amount_is_rejected(self, bad_limit):
        with pytest.raises(ValidationError):
            BudgetCreate(category_id="abc", month_year="2026-01", limit_amount=bad_limit)
