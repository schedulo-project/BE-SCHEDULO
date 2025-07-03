from django.db import models

from users.models import User


class Tag(models.Model):
    name = models.CharField(null=True, max_length=30)
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE, related_name="tag"
    )
    color = models.CharField(null=True, max_length=10)


class Schedule(models.Model):
    title = models.CharField(null=True, max_length=30)
    content = models.CharField(null=True, max_length=100)
    scheduled_date = models.DateField(null=True, auto_created=False, editable=True)
    deadline = models.DateField(null=True, auto_created=False, editable=True)
    is_completed = models.BooleanField(null=False, default=False)
    order_num = models.IntegerField(null=True)
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE, related_name="schedule"
    )
    tag = models.ManyToManyField(Tag, related_name="schedule")


class TimeTable(models.Model):
    subject = models.CharField(null=True, max_length=30)
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE, related_name="time_table"
    )
    DAY_CHOICES = [
        ("mon", "mon"),
        ("tue", "tue"),
        ("wed", "wed"),
        ("thu", "thu"),
        ("fri", "fri"),
        ("sat", "sat"),
        ("sun", "sun"),
    ]
    day_of_week = models.CharField(null=True, max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField(null=True, auto_created=False, editable=True)
    end_time = models.TimeField(null=True, auto_created=False, editable=True)
