from django.urls import path

from .views import (
    LoginAPIView, RegistrationAPIView, UserRetrieveUpdateAPIView,
    VerifyAPIView, PasswordResetRequestAPIView, ResetPasswordAPIView
)

app_name = "auth"

urlpatterns = [
    path('user/', UserRetrieveUpdateAPIView.as_view(), name='user'),
    path('users/', RegistrationAPIView.as_view(), name="register"),
    path('users/login/', LoginAPIView.as_view(), name="login"),
    path('users/verify/<token>', VerifyAPIView.as_view(), name='email-verify'),
    path('users/password_request/', PasswordResetRequestAPIView.as_view(),
         name="reset_request"),
    path('users/password_reset/',
         ResetPasswordAPIView.as_view(), name="password_reset"),
]
