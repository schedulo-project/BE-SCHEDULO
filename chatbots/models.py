from django.db import models
from users.models import User


class Chatting(models.Model):
    query = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.JSONField()
