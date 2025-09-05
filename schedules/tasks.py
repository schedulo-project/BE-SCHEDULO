from math import ceil
from django.db import transaction
from django.utils import timezone
from celery import shared_task
import pytz
import random

from users.models import User, StudyRoutine
from schedules.models import Schedule, TimeTable

from rest_framework import decorators, response

WEEKDAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
WEEKDAY_TO_INDEX = {d: i for i, d in enumerate(WEEKDAY_ORDER)}


def get_monday_of_week(dt):
    iso_weekday = dt.isoweekday()
    delta_days = iso_weekday - 1
    monday = (dt - timezone.timedelta(days=delta_days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday


def get_week_dates(reference_dt):
    tz = timezone.get_current_timezone()
    ref_local = timezone.localtime(reference_dt, tz)
    monday = get_monday_of_week(ref_local)
    dates = {}
    for i, code in enumerate(WEEKDAY_ORDER):
        dates[code] = (monday + timezone.timedelta(days=i)).date()
    return dates


def ensure_no_duplicate_and_create(user, title, content, scheduled_date):
    exists = Schedule.objects.filter(
        user=user, title=title, scheduled_date=scheduled_date
    ).exists()
    if not exists:
        schedule = Schedule.objects.create(
            user=user,
            title=title,
            content=content,
            scheduled_date=scheduled_date,
            deadline=scheduled_date,
        )
        schedule.save()
        print(schedule)


@shared_task
def generate_weekly_review_schedules():
    seoul_tz = pytz.timezone("Asia/Seoul")
    now_utc = timezone.now()
    now_seoul = now_utc.astimezone(seoul_tz)

    week_dates = get_week_dates(now_seoul)
    users = User.objects.all()

    for user in users:
        try:
            routine = StudyRoutine.objects.filter(user=user).first()
            if not routine or not routine.review_type:
                continue

            tts = list(TimeTable.objects.filter(user=user))
            if not tts:
                subject_names = [f"복습{i}" for i in range(1, 5)]
            else:
                subject_names = [tt.subject for tt in tts]

            review_type = routine.review_type.strip().upper()

            # 당일 복습
            if review_type == "SAMEDAY":
                with transaction.atomic():
                    # 과목 리스트의 각 요소에서 과목명, 요일 추출 -> 해당 요일에 해당 과목명으로 복습 일정 생성
                    for tt in tts:
                        day_code = (tt.day_of_week or "").strip().upper()
                        if day_code in week_dates:
                            scheduled_date = week_dates[day_code]
                            title = f"{tt.subject} 복습"
                            content = f"{tt.subject} 복습 스케줄"
                            ensure_no_duplicate_and_create(
                                user, title, content, scheduled_date
                            )
            else:
                # CUSTOM 요일 처리 (e.g. MON WED FRI)
                parts = [p.strip().upper() for p in review_type.split() if p.strip()]
                custom_codes = [p for p in parts if p in WEEKDAY_ORDER]
                if not custom_codes:
                    continue

                n_subjects = len(subject_names)
                n_days = len(custom_codes)

                # 과목 순서 랜덤
                shuffled_subjects = subject_names[:]
                random.shuffle(shuffled_subjects)

                # 요일별 배분: 기본 개수 + 나머지 처리
                base_count = n_subjects // n_days
                extra = n_subjects % n_days
                day_distribution = [
                    base_count + (1 if i < extra else 0) for i in range(n_days)
                ]

                subj_idx = 0
                with transaction.atomic():
                    for day_idx, code in enumerate(custom_codes):
                        scheduled_date = week_dates[code]  # 요일에 맞는 날짜
                        for _ in range(
                            day_distribution[day_idx]
                        ):  # 해당 요일의 배분 개수만큼 반복
                            subj = shuffled_subjects[subj_idx]
                            title = f"{subj} 복습"
                            content = f"{subj} 복습 스케줄"
                            ensure_no_duplicate_and_create(
                                user, title, content, scheduled_date
                            )
                            subj_idx += 1

        except Exception as e:
            print(f"generate_weekly_review_schedules error for user {user.pk}: {e}")


# API Test Version
@decorators.api_view(["POST"])
def generate_weekly_review_schedules_api_test(request):
    seoul_tz = pytz.timezone("Asia/Seoul")
    now_utc = timezone.now()
    now_seoul = now_utc.astimezone(seoul_tz)

    week_dates = get_week_dates(now_seoul)
    users = User.objects.all()

    for user in users:
        try:
            routine = StudyRoutine.objects.filter(user=user).first()
            if not routine or not routine.review_type:
                continue

            tts = list(TimeTable.objects.filter(user=user))
            if not tts:
                subject_names = [f"복습{i}" for i in range(1, 5)]
            else:
                subject_names = [tt.subject for tt in tts]

            review_type = routine.review_type.strip().upper()

            # 당일 복습
            if review_type == "SAMEDAY":
                with transaction.atomic():
                    # 과목 리스트의 각 요소에서 과목명, 요일 추출 -> 해당 요일에 해당 과목명으로 복습 일정 생성
                    for tt in tts:
                        day_code = (tt.day_of_week or "").strip().upper()
                        if day_code in week_dates:
                            scheduled_date = week_dates[day_code]
                            title = f"{tt.subject} 복습"
                            content = f"{tt.subject} 복습 스케줄"
                            ensure_no_duplicate_and_create(
                                user, title, content, scheduled_date
                            )
            else:
                # CUSTOM 요일 처리 (e.g. MON WED FRI)
                parts = [p.strip().upper() for p in review_type.split() if p.strip()]
                custom_codes = [p for p in parts if p in WEEKDAY_ORDER]
                if not custom_codes:
                    continue

                n_subjects = len(subject_names)
                n_days = len(custom_codes)

                # 과목 순서 랜덤
                shuffled_subjects = subject_names[:]
                random.shuffle(shuffled_subjects)

                # 요일별 배분: 기본 개수 + 나머지 처리
                base_count = n_subjects // n_days
                extra = n_subjects % n_days
                day_distribution = [
                    base_count + (1 if i < extra else 0) for i in range(n_days)
                ]

                subj_idx = 0
                with transaction.atomic():
                    for day_idx, code in enumerate(custom_codes):
                        scheduled_date = week_dates[code]  # 요일에 맞는 날짜
                        for _ in range(
                            day_distribution[day_idx]
                        ):  # 해당 요일의 배분 개수만큼 반복
                            subj = shuffled_subjects[subj_idx]
                            title = f"{subj} 복습"
                            content = f"{subj} 복습 스케줄"
                            ensure_no_duplicate_and_create(
                                user, title, content, scheduled_date
                            )
                            subj_idx += 1

        except Exception as e:
            print(f"generate_weekly_review_schedules error for user {user.pk}: {e}")
            return response.Response({"status": "error", "message": str(e)})

    return response.Response({"status": "success"})
