
import os
import uuid
from datetime import datetime

import httpx
import pytest

from tests.e2e.pages import AuthPage

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3000")
API_URL = os.environ.get("E2E_API_URL", "http://localhost:8000")


class Api:

    def __init__(self, token: str):
        self._http = httpx.Client(base_url=API_URL, headers={"Authorization": f"Bearer {token}"}, timeout=10)

    def category_id(self, name: str) -> str:
        return next(c["id"] for c in self._http.get("/api/categories").json() if c["name"] == name)

    def add_transaction(self, description: str, amount: float, category: str, type_: str = "expense", date: str = None):
        resp = self._http.post("/api/transactions", json={
            "type": type_, "amount": amount, "description": description,
            "category_id": self.category_id(category),
            "date": date or datetime.utcnow().replace(microsecond=0).isoformat(),
        })
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._http.close()


@pytest.fixture
def fresh_user_credentials():
    unique = uuid.uuid4().hex[:10]
    credentials = {
        "username": f"e2e_{unique}",
        "email": f"e2e-{unique}@example.com",
        "password": "e2e-test-password-1",
    }
    resp = httpx.post(f"{API_URL}/api/auth/register", json=credentials, timeout=10)
    resp.raise_for_status()
    return {**credentials, "token": resp.json()["access_token"]}


@pytest.fixture
def api(fresh_user_credentials):
    client = Api(fresh_user_credentials["token"])
    yield client
    client.close()


@pytest.fixture
def logged_in_page(page, fresh_user_credentials):
    auth = AuthPage(page).open()
    auth.log_in(fresh_user_credentials["email"], fresh_user_credentials["password"])
    auth.wait_until_signed_in()
    return page
