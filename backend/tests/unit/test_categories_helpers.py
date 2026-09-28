
import pytest
from bson import ObjectId

from app.routers.categories import cat_to_out

pytestmark = [
    pytest.mark.unit,
]


class TestCatToOut:
    def test_maps_all_fields(self):
        cat_id = ObjectId()
        cat = {"_id": cat_id, "name": "Food & Dining", "type": "expense", "icon": "utensils", "is_default": True}

        result = cat_to_out(cat)

        assert result == {
            "id": str(cat_id),
            "name": "Food & Dining",
            "type": "expense",
            "icon": "utensils",
            "is_default": True,
        }

    def test_icon_defaults_to_tag_when_absent(self):
        cat = {"_id": ObjectId(), "name": "Custom", "type": "expense"}
        result = cat_to_out(cat)
        assert result["icon"] == "tag"

    def test_is_default_defaults_to_false_when_absent(self):
        cat = {"_id": ObjectId(), "name": "Custom", "type": "income"}
        result = cat_to_out(cat)
        assert result["is_default"] is False

    def test_id_is_a_string_not_an_objectid(self):
        cat = {"_id": ObjectId(), "name": "Custom", "type": "income"}
        result = cat_to_out(cat)
        assert isinstance(result["id"], str)
