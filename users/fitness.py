import logging

from django.utils import timezone

from users.models import UserFitnessProfile

logger = logging.getLogger(__name__)

# VAM tiers (vertical meters/hour averaged over qualifying rides)
# Beginner < 200, Intermediate < 400, Advanced < 600, Elite >= 600
_VAM_TIERS = [
    (600, "elite"),
    (400, "advanced"),
    (200, "intermediate"),
    (0, "beginner"),
]


def _classify_tier(avg_vam: float) -> str:
    for threshold, tier in _VAM_TIERS:
        if avg_vam >= threshold:
            return tier
    return "beginner"


def sync_fitness_profile(user, client) -> UserFitnessProfile | None:
    try:
        activities = list(client.get_activities(limit=30))

        qualifying = []
        for activity in activities:
            activity_type = activity.type.root if activity.type else ""
            if activity_type not in ("Ride", "VirtualRide"):
                continue
            elevation_gain = float(activity.total_elevation_gain or 0)
            if elevation_gain <= 0:
                continue
            moving_time = activity.moving_time
            if moving_time is None:
                continue
            moving_time_s = float(moving_time)
            if moving_time_s < 60:
                continue
            vam = (elevation_gain / moving_time_s) * 3600
            qualifying.append(vam)

        if not qualifying:
            logger.info(
                "No qualifying rides found for user %s; skipping fitness profile sync",
                user.id,
            )
            return None

        avg_vam = sum(qualifying) / len(qualifying)
        tier = _classify_tier(avg_vam)

        profile, _ = UserFitnessProfile.objects.update_or_create(
            user=user,
            defaults={
                "avg_vam": avg_vam,
                "fitness_tier": tier,
                "rides_analyzed": len(qualifying),
                "last_synced_at": timezone.now(),
            },
        )
        logger.info(
            "Fitness profile synced for user %s: tier=%s avg_vam=%.1f rides=%d",
            user.id,
            tier,
            avg_vam,
            len(qualifying),
        )
        return profile

    except Exception:
        logger.exception("Failed to sync fitness profile for user %s", user.id)
        return None
