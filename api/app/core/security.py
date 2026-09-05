import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()
SESSION_DAYS = 7


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, encoded: str) -> bool:
    try:
        return _hasher.verify(encoded, plain)
    except (InvalidHashError, VerificationError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    secret = get_settings().auth_secret.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
