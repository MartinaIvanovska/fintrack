
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from jose import jwt

from app.core import security
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.core.config import settings

pytestmark = [
    pytest.mark.unit,
]


class TestPasswordHashing:
    def test_hash_is_not_the_plain_password(self):
        hashed = get_password_hash("correct-horse-battery-staple")
        assert hashed != "correct-horse-battery-staple"

    def test_correct_password_verifies(self):
        hashed = get_password_hash("my-secret-password")
        assert verify_password("my-secret-password", hashed) is True

    def test_incorrect_password_does_not_verify(self):
        hashed = get_password_hash("my-secret-password")
        assert verify_password("wrong-password", hashed) is False

    def test_hashing_the_same_password_twice_gives_different_hashes(self):
        first = get_password_hash("same-password")
        second = get_password_hash("same-password")
        assert first != second
        assert verify_password("same-password", first)
        assert verify_password("same-password", second)


class TestAccessTokenCreation:
    def test_token_encodes_the_subject(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-123"

    def test_token_has_an_expiry_claim(self):
        token = create_access_token({"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_custom_expires_delta_is_respected(self):
        token = create_access_token({"sub": "user-123"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["exp"] > 0

    def test_token_signed_with_wrong_key_fails_to_decode(self):
        token = create_access_token({"sub": "user-123"})
        with pytest.raises(jwt.JWTError):
            jwt.decode(token, "a-totally-different-key", algorithms=[settings.ALGORITHM])

    def test_tampered_token_fails_to_decode(self):
        token = create_access_token({"sub": "user-123"})
        header, payload, signature = token.split(".")
        i = len(signature) // 2
        signature = signature[:i] + ("A" if signature[i] != "A" else "B") + signature[i + 1:]
        tampered = f"{header}.{payload}.{signature}"
        with pytest.raises(jwt.JWTError):
            jwt.decode(tampered, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


class TestPasswordLengthBoundaries:

    @pytest.mark.parametrize("length", [71, 72], ids=["71-bytes", "72-bytes"])
    def test_last_byte_still_matters_up_to_72_bytes(self, length):
        hashed = get_password_hash("a" * (length - 1) + "X")
        assert verify_password("a" * (length - 1) + "Y", hashed) is False

    def test_multibyte_characters_count_in_bytes(self):
        hashed = get_password_hash("é" * 35 + "a")
        assert verify_password("é" * 35 + "b", hashed) is False

    @pytest.mark.xfail(strict=True, reason="bcrypt silently ignores everything after 72 bytes")
    def test_bytes_after_the_72nd_still_matter(self):
        hashed = get_password_hash("a" * 72 + "X")
        assert verify_password("a" * 72 + "Y", hashed) is False

    def test_empty_password_round_trips(self):
        assert verify_password("", get_password_hash("")) is True


class TestTokenExpiry:
    def _exp(self, token: str) -> datetime:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    def test_default_expiry_is_seven_days(self):
        expected = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        exp = self._exp(create_access_token({"sub": "user-123"}))
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7
        assert abs(exp - expected) < timedelta(seconds=60)

    def test_custom_expiry_replaces_the_default(self):
        expected = datetime.now(timezone.utc) + timedelta(minutes=5)
        exp = self._exp(create_access_token({"sub": "user-123"}, expires_delta=timedelta(minutes=5)))
        assert abs(exp - expected) < timedelta(seconds=60)

    def test_token_is_signed_with_the_configured_algorithm(self, monkeypatch):
        monkeypatch.setattr(settings, "ALGORITHM", "HS384")
        token = create_access_token({"sub": "user-123"})
        assert jwt.get_unverified_header(token)["alg"] == "HS384"
        assert jwt.decode(token, settings.SECRET_KEY, algorithms=["HS384"])["sub"] == "user-123"

    def test_input_claims_are_not_modified(self):
        claims = {"sub": "user-123"}
        create_access_token(claims)
        assert claims == {"sub": "user-123"}


USER_ID = ObjectId()


def _b64(part: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(part).encode()).rstrip(b"=").decode()


@pytest.fixture
def users_db(monkeypatch):
    db = MagicMock()
    db.users.find_one = AsyncMock(return_value={"_id": USER_ID, "email": "me@example.com"})
    monkeypatch.setattr(security, "get_db", lambda: db)
    return db


async def assert_rejected(token: str):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(token)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"
    assert exc.value.headers == {"WWW-Authenticate": "Bearer"}


class TestGetCurrentUser:
    async def test_valid_token_returns_the_stored_user(self, users_db):
        user = await get_current_user(create_access_token({"sub": str(USER_ID)}))
        assert user["email"] == "me@example.com"
        users_db.users.find_one.assert_awaited_once_with({"_id": USER_ID})

    async def test_token_for_a_user_that_no_longer_exists_is_rejected(self, users_db):
        users_db.users.find_one.return_value = None
        await assert_rejected(create_access_token({"sub": str(USER_ID)}))

    async def test_expired_token_is_rejected(self, users_db):
        await assert_rejected(create_access_token({"sub": str(USER_ID)}, expires_delta=timedelta(seconds=-1)))
        users_db.users.find_one.assert_not_awaited()

    async def test_token_without_subject_is_rejected(self, users_db):
        await assert_rejected(create_access_token({"role": "admin"}))

    @pytest.mark.parametrize("token", ["", "garbage", "a.b.c"], ids=["empty", "garbage", "three-parts"])
    async def test_malformed_token_is_rejected(self, users_db, token):
        await assert_rejected(token)

    async def test_token_signed_with_another_key_is_rejected(self, users_db):
        await assert_rejected(jwt.encode({"sub": str(USER_ID)}, "attacker-key", algorithm="HS256"))

    async def test_unsigned_alg_none_token_is_rejected(self, users_db):
        forged = _b64({"alg": "none", "typ": "JWT"}) + "." + _b64({"sub": str(USER_ID)}) + "."
        await assert_rejected(forged)

    async def test_token_with_a_different_algorithm_is_rejected(self, users_db):
        await assert_rejected(jwt.encode({"sub": str(USER_ID)}, settings.SECRET_KEY, algorithm="HS512"))

    @pytest.mark.xfail(strict=True, raises=InvalidId, reason="a subject that isn't an ObjectId raises instead of 401")
    async def test_subject_that_is_not_an_object_id_is_rejected(self, users_db):
        await assert_rejected(create_access_token({"sub": "not-an-object-id"}))

    @pytest.mark.xfail(strict=True, reason="tokens without an exp claim never expire")
    async def test_token_without_expiry_is_rejected(self, users_db):
        await assert_rejected(jwt.encode({"sub": str(USER_ID)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM))
