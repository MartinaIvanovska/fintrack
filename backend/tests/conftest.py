
import os

os.environ.setdefault("DB_NAME", "finance_tracker_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from bson import ObjectId
from hypothesis import HealthCheck, settings
from testcontainers.community.mongodb import MongoDbContainer


settings.register_profile("dev", max_examples=100, deadline=None)
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
    derandomize=True,
    print_blob=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile("fast", max_examples=10, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture
def new_object_id() -> ObjectId:
    return ObjectId()


@pytest.fixture
def make_object_id():
    def _make() -> ObjectId:
        return ObjectId()
    return _make


MONGO_IMAGE = "mongo:7.0"


@pytest.fixture(scope="session")
def mongo_uri():
    uri = os.environ.get("MONGO_URI")
    if uri:
        yield uri
        return
    with MongoDbContainer(MONGO_IMAGE) as container:
        yield container.get_connection_url()
