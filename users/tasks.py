from collections import defaultdict

from datetime import date, timedelta
from django.db import models
from django.db.models import Max
from celery import shared_task

from .models import *
from schedules.models import Schedule

def calculate_score_by_ratio(ratio, schedules_count):
    score = 0
    if ratio < 0.6: score -= 5
    elif ratio < 0.8: score += 5
    else: score += 10
    
    if schedules_count >= 5:
        score += 3
        if schedules_count >= 10: score += 5
    return score

# 연속 달성 보너스
def apply_streak_bonus(ratio_today, ratio_yesterday, ratio_two_days_ago):
    bonus = 0
    if ratio_today >= 0.8 and ratio_yesterday >= 0.8 and ratio_two_days_ago >= 0.8:
        bonus += 10
    if ratio_today < 0.6 and ratio_yesterday < 0.6:
        bonus -= 10
    return bonus

@shared_task
def calculate_score():
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # 유저 및 최고점 조회
    users = User.objects.annotate(
        highest_record=Max('scores__score')
    ).all()

    # 스케줄 데이터 로드 (N+1 방지)
    all_schedules = Schedule.objects.filter(
        user__in=users,
        scheduled_date__in=[today, yesterday, two_days_ago]
    ).values('user_id', 'scheduled_date', 'is_completed')
    
    sched_map = defaultdict(lambda: defaultdict(list))
    for s in all_schedules:
        sched_map[s['user_id']][s['scheduled_date']].append(s['is_completed'])

    # 이전 점수 로드
    past_scores = Score.objects.filter(user__in=users, date=yesterday).values('user_id', 'score')
    score_map = {s['user_id']: s['score'] for s in past_scores}

    # 오늘 생성됐는지 확인
    existing_today = set(Score.objects.filter(date=today).values_list('user_id', flat=True))

    new_scores_to_create = []

    for user in users:
        # 중복 스킵
        if user.id in existing_today:
            continue

        try:
            prev_score = score_map.get(user.id, 100)
            highest = user.highest_record or 100
            
            today_completed_list = sched_map[user.id][today]
            total_today = len(today_completed_list)
            
            # 일정 없으면 점수 유지
            if total_today == 0:
                new_scores_to_create.append(Score(user=user, score=prev_score, highest=highest, date=today))
                continue

            # 달성률 계산
            def calc_ratio(date_key):
                results = sched_map[user.id][date_key]
                if not results: return 0
                return sum(results) / len(results)

            ratio_today = calc_ratio(today)
            ratio_yesterday = calc_ratio(yesterday)
            ratio_two_days_ago = calc_ratio(two_days_ago)

            # 점수 합산
            current_score = prev_score + calculate_score_by_ratio(ratio_today, total_today)
            current_score += apply_streak_bonus(ratio_today, ratio_yesterday, ratio_two_days_ago)
            
            # 최고점 갱신
            highest = max(highest, current_score)

            new_scores_to_create.append(Score(
                user=user, score=current_score, highest=highest, date=today
            ))

        except Exception as e:
            print(f"Error [User {user.id}]: {e}")
            continue

    # 데이터 일괄 생성
    if new_scores_to_create:
        Score.objects.bulk_create(new_scores_to_create)

    # 백분위 일괄 갱신
    update_user_percentages(today)

def update_user_percentages(target_date):
    scores = Score.objects.filter(date=target_date).order_by("-score")
    total = scores.count()
    
    if total <= 1:
        scores.update(percentage=100.0)
        return

    # 백분위 계산 및 벌크 업데이트
    for index, score in enumerate(scores):
        score.percentage = round((index / total * 100), 2)
    
    Score.objects.bulk_update(scores, ['percentage'])