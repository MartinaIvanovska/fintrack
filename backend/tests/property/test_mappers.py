
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from hypothesis import given
from hypothesis import strategies as st

from app.routers.auth import user_to_out
from app.routers.categories import cat_to_out
from app.routers.transactions import enrich_transaction

pytestmark = pytest.mark.property

object_ids = st.builds(ObjectId)
text = st.text(max_size=50)
amounts = st.floats(min_value=0.01, max_value=1e12, allow_nan=False, allow_infinity=False)


@st.composite
def category_documents(draw):
    doc = {"_id": draw(object_ids), "name": draw(text), "type": draw(st.sampled_from(["income", "expense"]))}
    if draw(st.booleans()):
        doc["icon"] = draw(text)
    if draw(st.booleans()):
        doc["is_default"] = draw(st.booleans())
    return doc


@given(category_documents())
def test_cat_to_out_keeps_every_field_and_fills_defaults(doc):
    out = cat_to_out(doc)
    assert out == {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "type": doc["type"],
        "icon": doc.get("icon", "tag"),
        "is_default": doc.get("is_default", False),
    }


@given(
    _id=object_ids,
    username=text,
    email=st.emails(),
    created_at=st.datetimes(),
    password_hash=text,
)
def test_user_to_out_never_contains_the_password_hash(_id, username, email, created_at, password_hash):
    out = user_to_out({
        "_id": _id, "username": username, "email": email,
        "created_at": created_at, "hashed_password": password_hash,
    })
    assert set(out.model_dump()) == {"id", "username", "email", "created_at"}
    assert out.id == str(_id)


@given(
    amount=amounts,
    description=text,
    tx_type=st.sampled_from(["income", "expense"]),
    category_name=st.one_of(st.none(), text),
)
async def test_enrich_transaction_preserves_amount_and_resolves_category(amount, description, tx_type, category_name):
    db = MagicMock()
    db.categories.find_one = AsyncMock(return_value={"name": category_name} if category_name is not None else None)
    tx = {
        "_id": ObjectId(), "type": tx_type, "amount": amount, "date": "2026-01-15",
        "category_id": str(ObjectId()), "description": description,
    }

    out = await enrich_transaction(tx, db)

    assert out["amount"] == amount
    assert out["description"] == description
    assert out["type"] == tx_type
    assert out["category_name"] == (category_name if category_name is not None else "Unknown")
