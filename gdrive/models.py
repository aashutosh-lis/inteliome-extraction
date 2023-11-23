from django.db import models

# Create your models here.

class Credential(models.Model):
    token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    expiry = models.CharField(max_length=255)
    scopes = models.CharField(max_length=256)
    token_uri = models.CharField(max_length=256)
    client_id = models.CharField(max_length=256)
    client_secret = models.CharField(max_length=256)

