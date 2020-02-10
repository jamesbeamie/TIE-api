import re
import math
import datetime as dt

from django.core.exceptions import ValidationError

from rest_framework import serializers
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType

from todo.apps.authentication.serializers import RegistrationSerializer
from .models import Tasks
from ..authentication.serializers import RegistrationSerializer
from django.db.models import Avg


class TodoSerializer(serializers.ModelSerializer):
    """
        Todo model serializers
    """
    title = serializers.CharField(required=True)

    class Meta:
        model = Tasks
        fields = "__all__"

    def create_slug(self, title):
        """
            Create a slag
        """
        a_slug = slugify(title)
        origin = 1
        unique_slug = a_slug
        while Tasks.objects.filter(slug=unique_slug).exists():
            unique_slug = '{}-{}'.format(a_slug, origin)
            origin += 1
        slug = unique_slug
        return slug
