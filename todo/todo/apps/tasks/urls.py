from django.urls import path

from .views import (TodoAPIView, SpecificTodo)

app_name = "tasks"

urlpatterns = [
    path('todo/', TodoAPIView.as_view(), name="task"),
    path('todo/<str:slug>/', SpecificTodo.as_view(),
         name="specific/todo"),
]
