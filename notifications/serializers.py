from rest_framework import serializers
from users.models import User
from .models import WebPushSubscription


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["notify_today_schedule", "notify_deadline_schedule"]


class SubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField()
    expirationTime = serializers.CharField(allow_null=True, required=False)
    keys = serializers.DictField()

    def validate(self, attrs):
        keys = attrs.get("keys", {})
        if "p256dh" not in keys or "auth" not in keys:
            raise serializers.ValidationError("keys.p256dh, keys.auth 필수")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        endpoint = validated_data["endpoint"]
        keys = validated_data["keys"]
        obj, _ = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "p256dh": keys.get("p256dh", ""),
                "auth": keys.get("auth", ""),
                "user": user,
            },
        )
        return obj

    def to_representation(self, instance):
        """응답 데이터를 올바르게 구성"""
        return {
            "id": instance.id,
            "endpoint": instance.endpoint,
            "user": instance.user.id if instance.user else None,
            "created_at": instance.created_at,
            "is_active": instance.is_active,
        }
