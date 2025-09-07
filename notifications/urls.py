from notifications.views import *
from django.urls import path, include

app_name = "notifications"

urlpatterns = [
    path("fcm-token/", update_fcm_token, name="update-fcm-token"),
    path("fcm-test/", FCMTestView.as_view(), name="fcm-test"),
    path(
        "noti-setting/",
        NotificationSettingsView.as_view(),
        name="notification-setting",
    ),   
]
