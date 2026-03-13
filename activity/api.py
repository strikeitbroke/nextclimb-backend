import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from ninja import Query, Router
from ninja.errors import HttpError
from stravalib import Client

from activity.models import EmailSignup, SearchFeedback, StravaAuth
from activity.schemas import (
    EmailSignupRequest,
    EmailSignupResponse,
    ExplorerSegment,
    FeedbackRequest,
    FeedbackResponse,
    SearchPayloadSchema,
    SearchResponseSchema,
    SegmentBoundsSchema,
)
from activity.utils import (
    get_bounds,
    get_cached_segments,
    get_coors,
    normalize_query,
    set_cached_segments,
    split_bounds,
)

router = Router()
logger = logging.getLogger(__name__)


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


@router.get("/search")
def search(request, payload: Query[SearchPayloadSchema]):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    coors = get_coors(payload.location)
    if not coors:
        raise HttpError(500, "Coordinates could not be found for the provided location")

    bounds = get_bounds(coors, payload.radius)

    quadrants = split_bounds(bounds)

    # Check all caches first
    cache_results = [
        get_cached_segments(q.sw_lat, q.sw_lon, q.ne_lat, q.ne_lon)
        for q in quadrants
    ]

    def fetch_from_strava(index: int) -> tuple[int, str, list[dict]]:
        quadrant = quadrants[index]
        _, cache_key = cache_results[index]
        strava_explore_segments = client.explore_segments(
            quadrant.to_list(), activity_type="riding", min_cat=1, max_cat=4
        )
        quadrant_explorer = [ExplorerSegment(**s.__dict__) for s in strava_explore_segments]
        quadrant_data = [s.model_dump(mode="json") for s in get_response_schema(quadrant_explorer)]
        if quadrant_data:
            set_cached_segments(cache_key, quadrant_data)
        return index, cache_key, quadrant_data

    miss_indices = [i for i, (data, _) in enumerate(cache_results) if not data]
    strava_results: dict[int, list[dict]] = {}

    if miss_indices:
        with ThreadPoolExecutor(max_workers=len(miss_indices)) as executor:
            futures = {executor.submit(fetch_from_strava, i): i for i in miss_indices}
            for future in as_completed(futures):
                index, _, quadrant_data = future.result()
                strava_results[index] = quadrant_data

    cached_count = len(quadrants) - len(miss_indices)
    seen_ids: set[int] = set()
    all_segments: list[dict] = []

    for i, (cached_data, _) in enumerate(cache_results):
        segments = cached_data if cached_data else strava_results.get(i, [])
        for segment in segments:
            if segment["id"] not in seen_ids:
                seen_ids.add(segment["id"])
                all_segments.append(segment)

    if cached_count == 4:
        source = "cached"
    elif cached_count == 0:
        source = "strava"
    else:
        source = "partial_cache"

    return {"source": source, "segments": all_segments}


@router.post("/newsletter/signup", response=EmailSignupResponse)
def newsletter_signup(request, payload: EmailSignupRequest):
    EmailSignup.objects.get_or_create(email=payload.email)
    return {"ok": True}


@router.post("/feedback", response=FeedbackResponse)
def submit_feedback(request, payload: FeedbackRequest):
    SearchFeedback.objects.create(
        location=normalize_query(payload.location),
        radius=payload.radius,
        vote=payload.vote,
        comment=payload.comment,
    )
    return {"ok": True}
