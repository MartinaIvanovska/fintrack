
import json
import re
from pathlib import Path

import pytest

from tests.support.mongo_indexes import INDEXES

pytestmark = pytest.mark.unit

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "mongo-init").is_dir())
SOURCES = [
    REPO_ROOT / "mongo-init" / "init.js",
    REPO_ROOT / "kubernetes" / "mongo" / "mongo-init-configmap.yaml",
]

CREATE_INDEX = re.compile(r"db\.(\w+)\.createIndex\((\{[^}]*\})(?:,\s*(\{[^}]*\}))?\)")


def js_object_to_python(literal: str) -> dict:
    return json.loads(re.sub(r"(\w+)\s*:", r'"\1":', literal))


def parse_indexes(script: str) -> list:
    parsed = []
    for collection, keys, options in CREATE_INDEX.findall(script):
        parsed.append((
            collection,
            list(js_object_to_python(keys).items()),
            js_object_to_python(options) if options else {},
        ))
    return parsed


class TestParser:
    def test_parses_keys_and_options(self):
        script = 'db.users.createIndex({ email: 1 }, { unique: true });'
        assert parse_indexes(script) == [("users", [("email", 1)], {"unique": True})]

    def test_keeps_compound_key_order_and_directions(self):
        script = 'db.tx.createIndex({ user_id: 1, date: -1 });'
        assert parse_indexes(script) == [("tx", [("user_id", 1), ("date", -1)], {})]

    def test_parses_text_indexes(self):
        script = 'db.tx.createIndex({ description: "text", merchant: "text" });'
        assert parse_indexes(script) == [("tx", [("description", "text"), ("merchant", "text")], {})]


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_test_indexes_match_production_definitions(source):
    assert source.is_file(), f"{source} not found (is mongo-init/ mounted next to backend/?)"
    assert parse_indexes(source.read_text()) == INDEXES
