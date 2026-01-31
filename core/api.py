from ninja import NinjaAPI

from activity.api import router as activity_router
from users.api import router as user_router

api = NinjaAPI(title="NextClimb API")


api.add_router("/segment", activity_router)
api.add_router("/auth", user_router)
