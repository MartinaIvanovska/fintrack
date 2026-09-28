
from datetime import datetime

import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi import Header, HTTPException, status
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.core import database as db_module
from app.core.config import settings
from app.core.security import create_access_token, get_current_user, get_password_hash
from tests.support.factories import Factory
from tests.support.mongo_indexes import apply_indexes

TEST_DB_NAME = settings.DB_NAME


@pytest_asyncio.fixture(scope="session")
async def mongo_client(mongo_uri):
    assert "test" in TEST_DB_NAME, (
        f"Refusing to run integration tests against non-test database {TEST_DB_NAME!r}. "
        "Set the DB_NAME env var to something containing 'test'."
    )
    client = AsyncIOMotorClient(mongo_uri)
    await apply_indexes(client[TEST_DB_NAME])
    # Point the app's module-level `client` at our test client, so every
    # `get_db()` call made by the routers resolves to the test database.
    db_module.client = client
    yield client
    client.close()


@pytest_asyncio.fixture
async def db(mongo_client):
    return mongo_client[TEST_DB_NAME]


@pytest_asyncio.fixture(autouse=True)
async def clean_db(db):
    for name in await db.list_collection_names():
        await db[name].delete_many({})
    yield


# --- Users --------------------------------------------------------------
@pytest_asyncio.fixture
async def test_user(db):
    user_doc = {
        "username": "testuser",
        "email": "testuser@example.com",
        "hashed_password": get_password_hash("testpassword123"),
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return user_doc


@pytest_asyncio.fixture
async def other_user(db):
    user_doc = {
        "username": "otheruser",
        "email": "otheruser@example.com",
        "hashed_password": get_password_hash("otherpassword123"),
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return user_doc


@pytest_asyncio.fixture
async def category(db, test_user):
    cat_doc = {
        "name": "Food & Dining",
        "type": "expense",
        "icon": "utensils",
        "user_id": str(test_user["_id"]),
        "is_default": False,
        "created_at": datetime.utcnow(),
    }
    result = await db.categories.insert_one(cat_doc)
    cat_doc["_id"] = result.inserted_id
    return cat_doc


async def _resolve_test_user(authorization: str = Header(default=None)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    raw_id = authorization.removeprefix("Bearer ")
    if not ObjectId.is_valid(raw_id):
        return await get_current_user(raw_id)
    user_id = ObjectId(raw_id)

    db = db_module.client[TEST_DB_NAME]
    user = await db.users.find_one({"_id": user_id})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@pytest_asyncio.fixture
async def client(test_user):
    app.dependency_overrides[get_current_user] = _resolve_test_user
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {test_user['_id']}"}
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def other_client(other_user):
    app.dependency_overrides[get_current_user] = _resolve_test_user
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {other_user['_id']}"}
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def lenient_client(test_user):
    app.dependency_overrides[get_current_user] = _resolve_test_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    headers = {"Authorization": f"Bearer {test_user['_id']}"}
    async with AsyncClient(transport=transport, base_url="http://testserver", headers=headers) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def jwt_client():
    clients = []

    def _make(user: dict) -> AsyncClient:
        token = create_access_token({"sub": str(user["_id"])})
        ac = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers={"Authorization": f"Bearer {token}"},
        )
        clients.append(ac)
        return ac

    yield _make
    for ac in clients:
        await ac.aclose()


@pytest_asyncio.fixture
async def unauthenticated_client():
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def make(db):
    return Factory(db)



@pytest.fixture
def tx_payload(category):
    def _make(**overrides):
        payload = {
            "type": "expense",
            "amount": 25.5,
            "date": "2026-01-15T00:00:00",
            "category_id": str(category["_id"]),
            "description": "Groceries",
        }
        payload.update(overrides)
        return payload
    return _make
