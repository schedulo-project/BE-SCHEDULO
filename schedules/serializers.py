from rest_framework import serializers
from schedules.models import Tag, Schedule, TimeTable

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = "__all__"

class TimeTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTable
        fields = "__all__"