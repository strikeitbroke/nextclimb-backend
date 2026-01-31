import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from ninja import Router
from requests import HTTPError

from core import settings
from users.models import User
from users.schemas import AuthResponse, GoogleAuthRequest, UserResponse
from users.utils import RequiredJWTAuth, create_jwt

router = Router()
logger = logging.getLogger(__name__)


@router.post("/auth/google", response=AuthResponse)
def verify_google(request, data: GoogleAuthRequest):
    id_info = None
    try:
        id_info = id_token.verify_oauth2_token(
            data.token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        logger.info("can not verify id token from google")
        raise HTTPError(401, "invalid google token")

    if not id_info:
        return None

    user, created = User.objects.get_or_create(
        google_id=id_info["sub"],
        defaults={
            "email": id_info.get("email", ""),
            "name": id_info.get("name", ""),
            "picture": id_info.get("picture", ""),
        },
    )
    return {
        "token": create_jwt(user.id),
        "user": {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        },
    }


@router.get("/auth/me", response=UserResponse, auth=RequiredJWTAuth())
def get_current_user(request):
    user = request.auth
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }
