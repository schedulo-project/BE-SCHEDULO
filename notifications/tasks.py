from django.utils import timezone
from celery import shared_task
from firebase_admin import messaging
from django.contrib.auth import get_user_model

from notifications.utils import send_multi_channel
from schedules.models import Schedule
from collections import defaultdict

User = get_user_model()


def _build_body(titles, max_lines=10, max_chars=900):
    lines = titles[:max_lines]
    body = "\n".join(f"☐ {t}" for t in lines)
    if len(titles) > max_lines:
        body += f"\n…외 {len(titles) - max_lines}건"
    if len(body) > max_chars:
        body = body[: max_chars - 1] + "…"
    return body


@shared_task
def notify_today_schedule(content_title):
    today = timezone.localdate()
    print(f"📢 [Celery] 오늘의 일정 알림 작업 시작됨 {content_title}")

    rows = (
        Schedule.objects.filter(scheduled_date=today, is_completed=False)
        .values_list("user_id", "title")
        .distinct()
    )
    if not rows:
        print("ℹ️ 오늘 보낼 일정 없음")
        return

    titles_by_user = defaultdict(list)
    for r in rows:
        # Access the user_id and title using their tuple indices
        user_id = r[0]
        title = r[1]
        titles_by_user[user_id].append(title)

    users = User.objects.filter(
        id__in=titles_by_user.keys(), notify_today_schedule=True
    )

    for user in users.iterator():
        body_text = _build_body(titles_by_user[user.id])
        send_multi_channel(user, content_title, body_text)
        print(f"Sending notification to user {user.id} with body: {body_text}")


@shared_task
def notify_deadline_schedule():
    print("📢 [Celery] 마감 일정 알림 작업 시작됨")
    today = timezone.localdate()
    one_day_ahead = today + timezone.timedelta(days=1)
    seven_days_ahead = today + timezone.timedelta(days=7)

    _notify_deadline_by_day(one_day_ahead, "🚨 [하루 전] 마감 예정 일정이 있어요!")
    _notify_deadline_by_day(seven_days_ahead, "🚨 [7일 전] 마감 예정 일정이 있어요!")


def _notify_deadline_by_day(deadline, message_body):
    rows = Schedule.objects.filter(deadline=deadline, is_completed=False).values(
        "user_id", "title"
    )
    if not rows:
        print(f"ℹ️ {deadline} 기준 보낼 마감 없음")
        return

    titles_by_user = defaultdict(list)
    for r in rows:
        titles_by_user[r["user_id"]].append(r["title"])

    users = User.objects.filter(
        id__in=titles_by_user.keys(),
        notify_deadline_schedule=True,
    )

    for user in users.iterator():
        body_text = _build_body(titles_by_user[user.id])
        send_multi_channel(user, message_body, body_text)
