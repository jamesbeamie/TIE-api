from django.shortcuts import render

# Create your views here.
import json
import os
import re
from datetime import datetime, timedelta

import django
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.db import IntegrityError
from django.template import context
from django.template.loader import get_template, render_to_string
from requests.exceptions import HTTPError

import jwt
from todo.apps.authentication.validations import UserValidation
from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import swagger_auto_schema, swagger_serializer_method
from rest_framework import generics, status
from rest_framework.generics import (CreateAPIView, GenericAPIView,
                                     RetrieveUpdateAPIView, UpdateAPIView)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas import ManualSchema
from rest_framework.views import APIView, status
from social_core.backends.oauth import BaseOAuth1, BaseOAuth2
from social_core.exceptions import AuthForbidden, AuthTokenError, MissingBackend
from social_django.utils import load_backend, load_strategy

from .backends import GetAuthentication, JWTokens
from .models import User
from .renderers import UserJSONRenderer
from .serializers import (LoginSerializer, RegistrationSerializer,
                          ResetPasswordSerializer, UserSerializer)
from .utils import status_codes
from .validations import UserValidation


class RegistrationAPIView(GenericAPIView):
    # Allow any user (authenticated or not) to hit this endpoint.
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = RegistrationSerializer

    # the line above simply sets the swagger schema to be applied in this
    # class.
    # here, we're comfortable using the one defined in settings.py, which
    # currently,
    # is set to the default that ships with drf_yasg.

    # lets override some properties of the the default schema with our own
    # values
    def post(self, request):
        """
            POST /users/
        """
        user = request.data.get('user', {})
        url = request.data.get('site')
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        payload = {'email': serializer.data.get("email")}
        token = jwt.encode(payload, os.getenv("SECRET_KEY"),
                           algorithm='HS256').decode()
        from_mail, to_mail = os.getenv(
            "DEFAULT_FROM_EMAIL"), serializer.data.get("email")
        subject = "Account Verification"
        site_url = "http://"+get_current_site(request).domain
        email_url = url if url else site_url
        link_url = email_url + "/verify/{}".format(token)
        print('guURL',link_url)
        html_page = render_to_string(
            "email_verification.html",
            context={"link": link_url,
                     "user_name": serializer.data.get("username")
                     }
        )
        send_mail(subject, "Verification mail", from_mail, [
                  to_mail], fail_silently=False, html_message=html_page)
        return Response({
            "message": 'email_verify',
            "username": serializer.data['username'],
            "email": serializer.data['email']
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(GenericAPIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = LoginSerializer
    # Notice here that we do not call `serializer.save()` like we did for
    # the registration endpoint. This is because we don't actually have
    # anything to save. Instead, the `validate` method on our serializer
    # handles everything we need.

    # lets override some properties of the the default schema with our own
    # values
    def post(self, request):
        user = request.data.get('user', {})
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRetrieveUpdateAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        # There is nothing to validate or save here. Instead, we just want the
        # serializer to handle turning our `User` object into something that
        # can be JSONified and sent to the client.
        serializer = self.serializer_class(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # lets override some properties of the the default schema with our own
    # values
    def put(self, request, *args, **kwargs):
        serializer_data = request.data.get('user', {})

        # Here is that serialize, validate, save pattern we talked about
        # before.
        serializer = self.serializer_class(
            request.user, data=serializer_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerifyAPIView(GenericAPIView):
    """Verify endpoint holder"""
    serializer_class = UserSerializer

    # lets override some properties of the the default schema with our own
    # values
    def get(self, request, token):
        """
            GET /verify/
        """
        serializer = self.serializer_class()
        email = jwt.decode(token, os.getenv("SECRET_KEY"))["email"]
        user = User.objects.get(email=email)
        if user:
            user.is_confirmed = True
            user.save()
            token = JWTokens.create_token(self, user)
            return Response({
                "message": "Email Successfully Confirmed",
                'email': user.email,
                'username': user.username,
                'token': token
            }, status=status.HTTP_200_OK
            )
        else:
            return Response({
                "message": "No user of that email"
            }, status=status.HTTP_404_NOT_FOUND)


class PasswordResetRequestAPIView(GenericAPIView):
    """Sends Password reset link to email """
    serializer_class = ResetPasswordSerializer

    # lets override some properties of the the default schema with our own
    # values
    def post(self, request):
        user_data = request.data
        email = user_data['email']
        request_site = request.data.get("site")

        # confirms if an eamil has been provided
        # if email is not given then an error message is thrown
        if not email.strip():
            return Response({
                'message': 'no email provided',
            },
                status=status.HTTP_400_BAD_REQUEST)
        elif re.search(r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,3}$", email) is None:
            return Response({
                'message': 'bad email format'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Confirms if a user with the given email actually exists
        # If user exists then the user instance is returned
        # the user instance is used to generate a token
        # a response is given with the email and the generated token
        elif User.objects.filter(email=email).exists():
            # fetch username using the email
            username = User.objects.all().filter(email=email).first()

            payload = {
                'email': email,
                "iat": datetime.now(),
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            #paste frontend link
            reset_link = 'http://localhost:3000/authenticate-reset'
            subject = "Password Reset for royalframes media"
            message = render_to_string(
                'request_password_reset.html', {
                    'email': email,
                    'username': str(username).capitalize(),
                    'link': reset_link
                })
            to_email = email
            from_email = os.getenv("DEFAULT_FROM_EMAIL")
            send_mail(
                subject,
                message,
                from_email, [
                    to_email,
                ],
                html_message=message,
                fail_silently=False)
            message = {
                'Message': 'request successful',
            }
            return Response(message, status=status.HTTP_200_OK)

        # If user does not exist then an error is thrown to the user
        return Response({
            'message': 'unregistered email'},
            status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(UpdateAPIView):
    renderer_classes = (UserJSONRenderer,)
    serializer_class = UserSerializer
    # lets override some properties of the the default schema with our own
    # values
    def patch(self, request, *args, **kwargs):
        user_data = request.data
        email = user_data['email']
        user = User.objects.get(email=email)
        if user:
            password = user_data['password']
            UserValidation.valid_password(self, password)
            # save the password after we have validated it
            self.serializer_class.update(
                None,
                user,
                {
                    "password": password
                }
            )
            # Alert the user that the user has completed the password request
            return Response(
                {"message": "password changed"},
                status=status.HTTP_200_OK)
        return Response(
                {"message": "pwd updated unsuccesful"},
                status=status.HTTP_404_NOT_FOUND)
        
