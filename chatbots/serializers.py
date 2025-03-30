from rest_framework import serializers
from .models import Chatting


class ChattingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chatting
        fields = "__all__"
