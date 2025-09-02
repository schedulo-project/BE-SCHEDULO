from datetime import date, timedelta
from celery import shared_task
from .models import User, Score
from schedules.models import Schedule
from django.db.models import Max


def calculate_score_by_ratio(ratio, schedules_count):
    score = 0
    # 기본 비율 보상/패널티
    if ratio < 0.6:
        score -= 5
    elif ratio < 0.8:
        score += 5
    else:  # 0.8 이상
        score += 10

    # 일정 개수 보너스
    if schedules_count >= 5:
        score += 3
        if schedules_count >= 10:
            score += 5
    return score


def apply_streak_bonus(ratio_today, ratio_yesterday, ratio_two_days_ago):
    """
    연속 달성/실패 패턴에 따른 보너스/패널티 계산
    """
    bonus = 0

    # 3일 연속 일정 달성률 80% 이상 → +10점
    if ratio_today >= 0.8 and ratio_yesterday >= 0.8 and ratio_two_days_ago >= 0.8:
        bonus += 10

    # 2일 연속 60% 미만 → -10점
    if ratio_today < 0.6 and ratio_yesterday < 0.6:
        bonus -= 10

    return bonus


@shared_task
def calculate_score():
    users = User.objects.all()

    for user in users:
        # 기본 점수
        if not user.scores.exists():
            score = 100
            highest = score
        else:
            # 어제 점수 가져오기
            yesterday_score_obj = user.scores.filter(date=(date.today() - timedelta(days=1))).first()
            score = yesterday_score_obj.score if yesterday_score_obj else 100
            # 최고 점수 갱신
            highest = user.scores.aggregate(MaxScore=Max('score'))['MaxScore'] or 100

        # 오늘 일정 불러오기
        schedules = Schedule.objects.filter(user=user, scheduled_date=date.today())
        schedules_count = schedules.count()
        completed_schedules_count = schedules.filter(is_completed=True).count()

        # 일정 없는 경우 점수 변동 없음
        if schedules_count == 0:
            user_score = Score.objects.create(
                user=user,
                score=score,
                highest=highest,
                date=date.today()
            )
            user_score.save()
            continue

        # 오늘 달성률
        ratio_today = completed_schedules_count / schedules_count

        # 점수 계산
        score += calculate_score_by_ratio(ratio_today, schedules_count)

        # streak 보너스/패널티 적용
        ratio_yesterday, ratio_two_days_ago = 0, 0

        yesterday_schedules = Schedule.objects.filter(user=user, scheduled_date=(date.today() - timedelta(days=1)))

        if yesterday_schedules.exists():
            ratio_yesterday = yesterday_schedules.filter(is_completed=True).count() / yesterday_schedules.count()

        two_days_schedules = Schedule.objects.filter(user=user, scheduled_date=(date.today() - timedelta(days=2)))
        
        if two_days_schedules.exists():
            ratio_two_days_ago = two_days_schedules.filter(is_completed=True).count() / two_days_schedules.count()

        score += apply_streak_bonus(ratio_today, ratio_yesterday, ratio_two_days_ago)

        # 최고 점수 갱신
        highest = max(highest, score)

        # 오늘 점수 저장 (highest는 지금까지 최고 점수 반영)
        Score.objects.create(
            user=user,
            score=score,
            highest=highest,
            date=date.today()
        )

    # 오늘 점수 기준으로 백분위 갱신
    update_user_percentages()


def update_user_percentages():
    scores = list(Score.objects.filter(date=date.today()).order_by("-score"))
    total = len(scores)

    for index, score in enumerate(scores):
        percentage = round((index / total * 100), 2) if total > 1 else 100.0
        score.percentage = percentage
        score.save()
