from django.urls import path

from .views import (TodoAPIView, SpecificTodo)

app_name = "tasks"

urlpatterns = [
    path('item/', TodoAPIView.as_view(), name="task"),
    path('item/<str:slug>/', SpecificTodo.as_view(),
         name="specific/item"),
]
