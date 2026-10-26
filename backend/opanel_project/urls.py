from django.urls import path
from bridge import views, technical_views, upload_views, files_views

urlpatterns = [
    path("health/", views.health),
    path("auth/start/", views.start),
    path("auth/callback/", views.callback),
    path("auth/logout/", views.logout),
    path("api/csrf/", views.csrf_token),
    path("api/session/", views.session_status),
    path("api/websites/static/inspect/", upload_views.inspect_static_website),
    path("api/files/list/", files_views.list_account_directory),
    path("auth/technical-login/", technical_views.technical_login),
    path("api/technical-access/", technical_views.technical_access),
    path("api/technical-access/enroll/", technical_views.technical_enroll),
    path("", views.home),
]
