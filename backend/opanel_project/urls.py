from django.urls import path
from bridge import views

urlpatterns = [
    path("health/", views.health),
    path("auth/start/", views.start),
    path("auth/callback/", views.callback),
    path("auth/logout/", views.logout),
    path("api/session/", views.session_status),
    path("", views.home),
]
