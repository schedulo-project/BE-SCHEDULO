from firebase_admin import messaging
from django.contrib.auth import get_user_model

from notifications.sender import send_webpush

User = get_user_model()


def send_multi_channel(user: User, title: str, body: str):
    """
    FCM (user.fcm_token) 있으면 시도
    """
    # FCM
    if getattr(user, "fcm_token", None):
        try:
            msg = messaging.Message(
                data={"content_title": title, "body": body},
                token=user.fcm_token,
            )
            messaging.send(msg)
        except Exception as e:
            # FCM 토큰 만료 시 정리
            if "Requested entity was not found" in str(e):
                user.fcm_token = None
                user.save(update_fields=["fcm_token"])
