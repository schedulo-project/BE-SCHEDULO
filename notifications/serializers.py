from rest_framework import serializers
from users.models import User


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["notify_today_schedule", "notify_deadline_schedule"]
