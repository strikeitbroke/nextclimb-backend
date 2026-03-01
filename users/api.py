import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from ninja import Router
from ninja.errors import HttpError
from requests import HTTPError

from stravalib import Client

from core import settings
from users.fitness import sync_fitness_profile
from users.models import User, UserStrava
from users.schemas import AuthResponse, GoogleAuthRequest, StravaCallbackRequest, StravaStatusResponse, UserResponse
from users.utils import RequiredJWTAuth, create_jwt

router = Router()
logger = logging.getLogger(__name__)


@router.post("/google", response=AuthResponse)
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


@router.get("/me", response=UserResponse, auth=RequiredJWTAuth())
def get_current_user(request):
    user = request.auth
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }


@router.post("/strava/callback", response=StravaStatusResponse, auth=RequiredJWTAuth())
def strava_callback(request, data: StravaCallbackRequest):
    client = Client()
    try:
        token_response = client.exchange_code_for_token(
            client_id=int(settings.MY_STRAVA_CLIENT_ID),
            client_secret=settings.MY_STRAVA_CLIENT_SECRET,
            code=data.code,
        )
    except Exception:
        logger.info("failed to exchange strava code for token")
        raise HttpError(400, "invalid strava code")

    athlete = client.get_athlete()
    user: User = request.auth

    UserStrava.objects.update_or_create(
        user=user,
        defaults={
            "athlete_id": str(athlete.id),
            "access_token": token_response["access_token"],
            "refresh_token": token_response["refresh_token"],
            "expires_at": token_response["expires_at"],
            "scope": "",
        },
    )

    sync_fitness_profile(user, client)

    return {"connected": True}


@router.post("/strava/resync", response=StravaStatusResponse, auth=RequiredJWTAuth())
def strava_resync(request):
    user: User = request.auth
    try:
        user_strava = UserStrava.objects.get(user=user)
    except UserStrava.DoesNotExist:
        raise HttpError(400, "Strava account not connected")

    client = Client()
    try:
        user_strava.check_and_refresh(client)
    except Exception:
        logger.info("Strava token refresh failed for user %s", user.id)
        raise HttpError(401, "Strava token expired, please reconnect")

    client.access_token = user_strava.access_token
    sync_fitness_profile(user, client)
    return {"connected": True}


@router.get("/strava/status", response=StravaStatusResponse, auth=RequiredJWTAuth())
def strava_status(request):
    user: User = request.auth
    return {"connected": UserStrava.objects.filter(user=user).exists()}
