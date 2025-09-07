from firebase_admin import messaging
from django.contrib.auth import get_user_model

from notifications.models import WebPushSubscription
from notifications.sender import send_webpush

User = get_user_model()


def send_multi_channel(user: User, title: str, body: str):
    """
    1) FCM (user.fcm_token) 있으면 시도
    2) WebPush 구독들(iOS/사파리) 있으면 모두 시도
    실패/만료 토큰/구독은 정리
    """
    # 1) FCM
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

    # 2) Web Push (여러 개 가능)
    for sub in WebPushSubscription.objects.filter(user=user):
        try:
            send_webpush(sub, {"title": title, "body": body})
        except Exception:
            # sender에서 404/410은 내부에서 삭제됨. 여기선 무시.
            pass
