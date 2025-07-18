from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls")),
    path("schedules/", include("schedules.urls")),
    path("chatbots/", include("chatbots.urls")),
    path("notifications/", include("notifications.urls")),
]
