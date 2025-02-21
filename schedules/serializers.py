from rest_framework import serializers
from schedules.models import Tag, Schedule, TimeTable

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"

class ScheduleSerializer(serializers.ModelSerializer):
    tag = TagSerializer(required=False, many=True)
    
    class Meta:
        model = Schedule
        fields = "__all__"
        extra_kwargs = {'content': {'required': False}, 'deadline': {'required': False}, 
                        'order_num': {'required': False}, 'is_completed': {'required': False}}

class TimeTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTable
        fields = "__all__"