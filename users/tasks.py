from datetime import date, timedelta
from celery import shared_task
from .models import User, Score
from schedules.models import Schedule


@shared_task
def calculate_score(request):
    users = User.objects.all()
    score = 0
    score_one_day_ago = 0
    score_two_days_ago = 0
    for user in users:
        if user.scores.all().exists():
            if user.scores.filter(date=date.today()).exists():
                return
            if user.scores.filter(date=(date.today() - timedelta(days=1))).exists():
                score_one_day_ago = (
                    user.scores.filter(date=(date.today() - timedelta(days=1)))
                    .first()
                    .score
                )
                score = score_one_day_ago
                if user.scores.filter(date=(date.today() - timedelta(days=2))).exists():
                    score_two_days_ago = (
                        user.scores.filter(date=(date.today() - timedelta(days=2)))
                        .first()
                        .score
                    )
        else:
            score = 100

        schedules = Schedule.objects.filter(user=user, scheduled_date=date.today())
        schedules_count = schedules.count()
        completed_schedules_count = schedules.filter(is_completed=True).count()

        if schedules_count == 0:
            user_score = Score.objects.create(user=user, score=score, date=date.today())
            user_score.save()
            return

        ratio = completed_schedules_count / schedules_count

        if ratio < 0.6:
            score -= 5
        elif ratio < 0.8:
            score += 5
        else:
            score += 10

        if schedules_count >= 5:
            score += 3
            if schedules_count >= 10:
                score += 5

        user_score = Score.objects.create(user=user, score=score, date=date.today())
        user_score.save()

        return
