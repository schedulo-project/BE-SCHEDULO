# apps/push/sender.py
import json, os
from pywebpush import webpush, WebPushException

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")


def send_webpush(subscription, payload: dict, ttl=60):
    if not VAPID_PRIVATE_KEY:
        raise RuntimeError("VAPID_PRIVATE_KEY 환경 변수를 설정하세요.")
    try:
        return webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),  # {"title":"...", "body":"..."}
            vapid_private_key=VAPID_PRIVATE_KEY,
            ttl=ttl,
        )
    except WebPushException as e:
        # 404/410 → 만료된 구독 정리
        code = getattr(e.response, "status_code", None)
        if code in (404, 410):
            subscription.delete()
        else:
            raise
