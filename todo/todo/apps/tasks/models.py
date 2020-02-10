from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.template.defaultfilters import slugify

from todo.apps.authentication.models import User


class Tasks(models.Model):
    """
        Each Todo model schema
    """
    slug = models.SlugField(max_length=255)
    title = models.CharField(db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return self.title
