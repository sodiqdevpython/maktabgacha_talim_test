from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/home/", views.home),
    path("api/sessions/", views.start_session),
    path("api/sessions/<int:pk>/", views.session_detail),
    path("api/sessions/<int:pk>/answer/", views.answer),
    path("api/sessions/<int:pk>/result/", views.result),
]
