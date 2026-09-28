
import socket
import threading
import time

import pymongo
import pytest
import requests
import uvicorn

from app.core import database as db_module
from app.core.config import settings
from app.main import app
from tests.support.mongo_indexes import INDEXES

API_USER = {"username": "fuzzer", "email": "fuzzer@example.com", "password": "fuzzer-password-1"}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def api_base_url(mongo_uri):w
    assert "test" in settings.DB_NAME, f"refusing to fuzz non-test database {settings.DB_NAME!r}"
    original_uri, original_client = settings.MONGO_URI, db_module.client
    settings.MONGO_URI = mongo_uri

    with pymongo.MongoClient(mongo_uri) as client:
        client.drop_database(settings.DB_NAME)
        for collection, keys, options in INDEXES:
            client[settings.DB_NAME][collection].create_index(keys, **options)

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            raise RuntimeError("the API server did not start")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    settings.MONGO_URI, db_module.client = original_uri, original_client


@pytest.fixture(scope="session")
def auth_headers(api_base_url):
    resp = requests.post(f"{api_base_url}/api/auth/register", json=API_USER, timeout=10)
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def fresh_data(mongo_uri):
    with pymongo.MongoClient(mongo_uri) as client:
        db = client[settings.DB_NAME]
        for name in ("transactions", "budgets", "categories"):
            db[name].delete_many({})
