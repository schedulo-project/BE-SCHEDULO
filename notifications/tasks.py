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

    users = User.objects.filter(
        id__in=users_ids, notify_today_schedule=True, fcm_token__isnull=False
    ).exclude(fcm_token="")

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


@shared_task
def notify_deadline_schedule():
    print("📢 [Celery] 마감 일정 알림 작업 시작됨")
    today = timezone.localdate()
    one_day_ahead = today + timezone.timedelta(days=1)
    seven_days_ahead = today + timezone.timedelta(days=7)

    _notify_deadline_by_day(one_day_ahead, "🚨 [하루 전] 마감 예정 일정이 있어요!")
    _notify_deadline_by_day(seven_days_ahead, "🚨 [7일 전] 마감 예정 일정이 있어요!")


def _notify_deadline_by_day(deadline, message_body):
    schedules = Schedule.objects.filter(deadline=deadline, is_completed=False)
    user_ids = schedules.values_list("user_id", flat=True).distinct()
    users = User.objects.filter(
        id__in=user_ids, notify_deadline_schedule=True, fcm_token__isnull=False
    ).exclude(fcm_token="")
    for user in users:
        user_schedules = schedules.filter(user=user)
        if not user_schedules.exists():
            continue
        schedule_titles = [f"☐ {s.title}" for s in user_schedules]
        body_text = " \n".join(schedule_titles)

        message = messaging.Message(
            data={
                "content_title": message_body,
                "body": body_text,
            },
            token=user.fcm_token,
        )
        try:
            response = messaging.send(message)
            print(f"✅ {user.email} 알림 전송 완료: {response}")
        except Exception as e:
            print(f"❌ {user.email} 전송 실패: {e}")
