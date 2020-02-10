from django.shortcuts import render

# Create your views here.
import datetime as dt
import json
import os
import random
import re
from datetime import datetime, timedelta

import django
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string

from todo.apps.authentication.utils import status_codes, swagger_body
from todo.apps.core.pagination import PaginateContent
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema, swagger_serializer_method
from rest_framework import exceptions, generics, status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.views import Response

from .models import Tasks, User
from .renderers import TodoJSONRenderer
from .serializers import TodoSerializer


class TodoAPIView(generics.ListCreateAPIView):
    """
        todo endpoints
    """
    queryset = Tasks.objects.all()
    serializer_class = TodoSerializer

    def post(self, request):
        """
            POST /photography/todo/todo/
        """
        permission_classes = (IsAuthenticatedOrReadOnly,)
        if permission_classes:
            context = {"request": request}
            todo = request.data.copy()
            todo['slug'] = TodoSerializer(
            ).create_slug(request.data['title'])
            serializer = self.serializer_class(data=todo, context=context)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            serializer.errors,
            status=status.HTTP_401_UNAUTHORIZED
        )

    def get(self, request):
        """
            GET /photography/todo/todo/
        """
        perform_pagination = PaginateContent()
        objs_per_page = perform_pagination.paginate_queryset(
            self.queryset, request)
        serializer = TodoSerializer(
            objs_per_page,
            context={
                'request': request
            },
            many=True
        )
        return perform_pagination.get_paginated_response(serializer.data)


class SpecificTodo(generics.RetrieveUpdateDestroyAPIView):
    """
        Specific todo endpoint class
    """
    serializer_class = TodoSerializer

    def get(self, request, slug, *args, **kwargs):
        """
            GET /todo/todo/<slug>/
        """
        try:
            todo = Tasks.objects.get(slug=slug)
        except Tasks.DoesNotExist:
            raise exceptions.NotFound({
                "message": 'todo not found'
            })
        # this checks if an istance of read exists
        # if it doesn't then it creates a new one
        serializer = TodoSerializer(
            todo,
            context={
                'request': request
            }
        )
        return Response(serializer.data, status=200)

    def delete(self, request, slug, *args, **kwargs):
        """
            DELETE /photography/todo/todo/<slug>/
        """
        permission_classes = (IsAuthenticated,)
        try:
            todo = Tasks.objects.get(slug=slug)
        except Tasks.DoesNotExist:
            raise exceptions.NotFound({
                "message": 'todo not found'
            })
        todo.delete()
        return Response({
            "todo": 'deleted'
        }, status=204)

    def put(self, request, slug, *args, **kwargs):
        """
            PUT /photography/todo/todo/<slug>/
        """
        permission_classes = (IsAuthenticated,)
        todo = get_object_or_404(Tasks.objects.all(), slug=slug)
        todo_data = request.data
        todo.updated_at = dt.datetime.utcnow()
        serializer = TodoSerializer(
            instance=todo,
            data=todo_data,
            context={'request': request},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                [
                    serializer.data,
                    {"message": 'todo updated'}
                ], status=201
            )
        else:
            return Response(
                serializer.errors,
                status=400
            )


def get_todo(slug):
    """
        Returns specific todo using slug
    """
    todo = Tasks.objects.all().filter(slug=slug).first()
    if todo is None:
        raise exceptions.NotFound({
            "message": 'todo not found'
        }, status.HTTP_404_NOT_FOUND)
    return todo
