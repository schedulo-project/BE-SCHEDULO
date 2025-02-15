from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    name = models.CharField(null=True, max_length=10)
    email = models.EmailField(null=True)
    first_name, last_name = None, None

class StudyRoutine(models.Model):
    weeks_before_exam = models.IntegerField(null=True)
    review_type = models.CharField(null=True, max_length=30)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name="study_routine")
