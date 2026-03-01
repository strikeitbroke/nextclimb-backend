import os
import time

from django.conf import settings
from django.db import models
from django.utils import timezone


class StravaAuth(models.Model):
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expires_at = models.BigIntegerField()  # Stores the POSIX timestamp

    def is_expired(self):
        """Checks if the current access token is still valid."""
        return time.time() > self.expires_at

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


class GeocodedLocation(models.Model):
    # The clean version from the API (e.g. "San Jose, California, USA")
    user_query = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
