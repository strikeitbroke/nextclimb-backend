from django.db import models
from django.utils import timezone

from core import settings


class User(models.Model):
    google_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255)
    name = models.CharField(max_length=255)
    picture = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<{self.email}>"


class UserStrava(models.Model):
    athlete_id = models.CharField(max_length=255, unique=True)
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.BigIntegerField()  # Stores the POSIX timestamp
    scope: models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_refresh(self, client):
        # Use a 5-minute (300s) buffer for safety
        if timezone.now().timestamp() + 300 >= self.expires_at:
            res = client.refresh_access_token(
                client_id=settings.MY_STRAVA_CLIENT_ID,
                client_secret=settings.MY_STRAVA_CLIENT_SECRET,
                refresh_token=self.refresh_token,
            )
            self.access_token = res["access_token"]
            self.refresh_token = res["refresh_token"]
            self.expires_at = res["expires_at"]
            self.save()
            return True  # Refreshed
        return False  # Still valid
