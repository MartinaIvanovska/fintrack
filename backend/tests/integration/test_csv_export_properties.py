
import csv
import io
from datetime import datetime

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

pytestmark = [
    pytest.mark.integration,
    pytest.mark.property,
    pytest.mark.asyncio(loop_scope="session"),
]

HEADER = ["Date", "Type", "Description", "Amount", "Category", "Payment Method", "Merchant"]

csv_special = st.sampled_from(',"\n\r;\t \'')
tricky_text = st.tuples(
    st.sampled_from(["", "", "=", "+", "-", "@"]),
    st.lists(st.one_of(csv_special, csv_special, st.characters(codec="utf-8")), max_size=30).map("".join),
).map("".join)
money = st.integers(min_value=1, max_value=1_000_000_000).map(lambda cents: cents / 100)


@st.composite
def transactions(draw):
    return {
        "type": draw(st.sampled_from(["income", "expense"])),
        "amount": draw(money),
        "date": datetime(2026, 1, draw(st.integers(min_value=1, max_value=31)), draw(st.integers(0, 23))),
        "description": draw(tricky_text),
        "merchant": draw(st.one_of(st.none(), tricky_text)),
        "payment_method": draw(st.one_of(st.none(), st.sampled_from(["card", "cash", "bank transfer"]))),
    }


def parse_csv(body: str) -> list:
    return list(csv.reader(io.StringIO(body, newline="")))

@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(category_name=tricky_text, txs=st.lists(transactions(), min_size=1, max_size=8))
async def test_every_value_survives_the_csv_round_trip(make, jwt_client, category_name, txs):
    texts = [category_name] + [tx["description"] for tx in txs] + [tx["merchant"] or "" for tx in txs]
    for label, found in [
        ("has a line break", any(c in t for t in texts for c in "\r\n")),
        ("has a double quote", any('"' in t for t in texts)),
        ("has a comma", any("," in t for t in texts)),
        ("starts like a formula (= + - @)", any(t[:1] in ("=", "+", "-", "@") for t in texts)),
        ("has non-ASCII text", any(not t.isascii() for t in texts)),
    ]:
        if found:
            event(label)

    user = await make.user()
    category = await make.category(user, name=category_name)
    for tx in txs:
        await make.transaction(user, category, **tx)

    resp = await jwt_client(user).get("/api/reports/export/csv", params={"month_year": "2026-01"})

    assert resp.status_code == 200
    header, *rows = parse_csv(resp.text)
    assert header == HEADER
    expected = [
        [
            tx["date"].strftime("%Y-%m-%d"),
            tx["type"],
            tx["description"],
            repr(tx["amount"]),
            category_name,
            tx["payment_method"] or "",
            tx["merchant"] or "",
        ]
        for tx in txs
    ]
    assert sorted(rows) == sorted(expected)
