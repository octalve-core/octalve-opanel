from django.urls import path
from bridge import views

urlpatterns = [
    path("health/", views.health),
    path("auth/start/", views.start),
    path("auth/callback/", views.callback),
    path("auth/logout/", views.logout),
    path("api/csrf/", views.csrf_token),
    path("api/session/", views.session_status),
    path("api/websites/static/inspect/", views.inspect_static_website),
    path("auth/technical-login/", views.technical_login),
    path("api/technical-access/", views.technical_access),
    path("api/technical-access/enroll/", views.technical_enroll),
    path("", views.home),
]
