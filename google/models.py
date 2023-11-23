from django.db import models

class Credential(models.Model):
    access_token=models.CharField(max_length=100)
