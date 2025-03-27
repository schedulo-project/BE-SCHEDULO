from django.db import models
from users.models import User


class Chatting(models.Model):
    query = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.OneToOneField("Answer", on_delete=models.CASCADE)


class Answer(models.Model):
    tag = models.CharField(max_length=100)
    date = models.DateField(auto_created=False)
    method = models.CharField(max_length=100)
    details = models.CharField(max_length=100)
