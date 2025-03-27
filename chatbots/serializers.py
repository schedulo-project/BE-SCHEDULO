from rest_framework import serializers
from .models import Chatting, Answer


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"


class ChattingSerializer(serializers.ModelSerializer):
    answer = AnswerSerializer()

    class Meta:
        model = Chatting
        fields = "__all__"
