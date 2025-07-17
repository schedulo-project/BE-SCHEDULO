from django.utils import timezone
from celery import shared_task
from firebase_admin import messaging
from django.contrib.auth import get_user_model

from schedules.models import Schedule

User = get_user_model()


@shared_task
def notify_today_schedule(content_title):
    now = timezone.localtime()
    print(f"📢 [Celery] 오늘의 일정 알림 작업 시작됨 {content_title}")
    today = now.date()

    users_ids = (
        Schedule.objects.filter(scheduled_date=today, is_completed=False)
        .values_list("user_id", flat=True)
        .distinct()
    )

    users = User.objects.filter(id__in=users_ids, fcm_token__isnull=False).exclude(
        fcm_token=""
    )

    for user in users:
        schedules = Schedule.objects.filter(
            user=user, scheduled_date=today, is_completed=False
        )

        if not schedules.exists():
            continue

        schedule_titles = [f"☐ {s.title}" for s in schedules]

        body_text = "\n".join(schedule_titles)

        message = messaging.Message(
            data={
                "content_title": content_title,
                "body": body_text,
            },
            token=user.fcm_token,
        )
        try:
            response = messaging.send(message)
            print(f"✅ {user.email} 알림 전송 완료: {response}")
        except Exception as e:
            print(f"❌ {user.email} 전송 실패: {e}")
            if "Requested entity was not found" in str(e):
                user.fcm_token = None
                user.save(update_fields=["fcm_token"])
