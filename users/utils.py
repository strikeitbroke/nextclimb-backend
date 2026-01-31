import jwt
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from ninja.security import HttpBearer

from core import settings
from users.models import User


def create_jwt(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": timezone.now()
        + timezone.timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_google_token(token: str) -> dict | None:
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        return None


def _get_user_from_token(token: str) -> User | None:
    """Shared logic for extracting user from JWT."""
    payload = verify_jwt(token)
    if payload is None:
        return None
    try:
        return User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        return None


class RequiredJWTAuth(HttpBearer):
    def authenticate(self, request, token: str) -> User | None:
        return _get_user_from_token(token)


class OptionalJWTAuth(HttpBearer):
    def authenticate(self, request, token: str) -> User | None:
        if not token:
            return None
        return _get_user_from_token(token)
