
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.core import database as db_module
from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


async def test_health_check_needs_no_authentication(unauthenticated_client):
    resp = await unauthenticated_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_startup_opens_and_shutdown_closes_the_database_client(mongo_client):
    original = db_module.client
    try:
        await app.router.startup()
        opened = db_module.client
        assert isinstance(opened, AsyncIOMotorClient)
        assert opened is not original
        await app.router.shutdown()
    finally:
        db_module.client = original


async def test_shutdown_without_a_client_does_nothing(mongo_client):
    original = db_module.client
    try:
        db_module.client = None
        await db_module.close_db()  # must not raise
        assert db_module.client is None
    finally:
        db_module.client = original
