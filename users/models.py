from django.db import models


class User(models.Model):
    google_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=255)
    name = models.CharField(max_length=255)
    picture = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<{self.email}>"
