import logging

from ninja import Query, Router
from ninja.errors import HttpError
from stravalib import Client

from activity.models import StravaAuth
from activity.schemas import (
    ExplorerSegment,
    SearchPayloadSchema,
    SearchResponseSchema,
    SegmentBoundsSchema,
    SegmentSearchResponse,
)
from activity.utils import (
    get_bounds,
    get_cached_segments,
    get_coors,
    set_cached_segments,
)
from users.models import UserFitnessProfile
from users.utils import OptionalJWTAuth

router = Router()
logger = logging.getLogger(__name__)

_DIFFICULTY_SCORE = {
    "Easy":     {"beginner": 3, "intermediate": 2, "advanced": 1, "elite": 0},
    "Moderate": {"beginner": 2, "intermediate": 3, "advanced": 2, "elite": 1},
    "Hard":     {"beginner": 1, "intermediate": 2, "advanced": 3, "elite": 2},
    "Brutal":   {"beginner": 0, "intermediate": 1, "advanced": 2, "elite": 3},
}


def rank_segments_for_user(segments, fitness_tier):
    return sorted(
        segments,
        key=lambda s: _DIFFICULTY_SCORE.get(s["difficulty"], {}).get(fitness_tier, 1),
        reverse=True,
    )


@router.post("/")
def get_segment(request, payload: SegmentBoundsSchema):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    bounds = (
        payload.sw_lat,
        payload.sw_lon,
        payload.ne_lat,
        payload.ne_lon,
    )

    segments = client.explore_segments(
        bounds, activity_type="riding", min_cat=1, max_cat=4
    )  # Get current athlete details
    data = [s.model_dump(mode="json") for s in segments]

    return data


def get_response_schema(explore_segments: list[ExplorerSegment]):
    response_schema: list[SearchResponseSchema] = []

    for item in explore_segments:
        response_schema.append(
            SearchResponseSchema(
                id=item.id,
                name=item.name,
                difficulty=item.get_difficulty(),
                distance=item.to_miles(),
                avg_grade=item.avg_grade,
                start_latlng=item.start_latlng,
                end_latlng=item.end_latlng,
                elev_difference=item.elev_difference,
            )
        )
    return response_schema


@router.get("/search", response=SegmentSearchResponse, auth=OptionalJWTAuth())
def search(request, payload: Query[SearchPayloadSchema]):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    coors = get_coors(payload.location)
    if not coors:
        raise HttpError(500, "Coordinates could not be found for the provided location")

    bounds = get_bounds(coors, payload.radius)

    cached_data, cache_key = get_cached_segments(
        bounds.sw_lat, bounds.sw_lon, bounds.ne_lat, bounds.ne_lon
    )
    if cached_data:
        source = "cached"
        segments = cached_data
    else:
        strava_explore_segments = client.explore_segments(
            bounds.to_list(), activity_type="riding", min_cat=1, max_cat=4
        )
        explore_segments: list[ExplorerSegment] = [
            ExplorerSegment(**s.__dict__) for s in strava_explore_segments
        ]
        response_schema = get_response_schema(explore_segments)
        segments = [s.model_dump(mode="json") for s in response_schema]
        if segments:
            set_cached_segments(cache_key, segments)
        source = "strava"

    personalized = False
    user = request.auth if request.auth != "anonymous" else None
    if user is not None:
        try:
            profile = UserFitnessProfile.objects.get(user=user)
            segments = rank_segments_for_user(segments, profile.fitness_tier)
            personalized = True
        except UserFitnessProfile.DoesNotExist:
            pass

    return {"source": source, "segments": segments, "personalized": personalized}
