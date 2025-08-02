from collections import defaultdict
from rest_framework import serializers
from schedules.models import Tag, Schedule, TimeTable


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color"]
        extra_kwargs = {
            "color": {"required": False},
        }


class ScheduleListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        user = self.context["request"].user
        schedules = []
        for item in validated_data:
            item.pop("tag", None)
            schedules.append(Schedule(**item, user=user))

        return Schedule.objects.bulk_create(schedules)


class ScheduleSerializer(serializers.ModelSerializer):
    tag = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = "__all__"
        extra_kwargs = {
            "content": {"required": False},
            "deadline": {"required": False},
            "order_num": {"required": False},
            "is_completed": {"required": False},
            "tag": {"read_only": True},
        }
        list_serializer_class = ScheduleListSerializer

    def get_tag(self, obj):
        tags = obj.tag.all()
        return TagSerializer(tags, many=True).data


class GroupedScheduleSerializer(serializers.Serializer):
    schedules = serializers.SerializerMethodField()

    def get_schedules(self, obj):
        schedule_data = obj.order_by("scheduled_date")  # 날짜순 정렬
        serialized_data = ScheduleSerializer(schedule_data, many=True).data

        grouped_by_date = defaultdict(list)

        for item in serialized_data:
            date = item.pop("scheduled_date", None)
            grouped_by_date[date].append(item)

        return grouped_by_date


class TimeTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeTable
        fields = "__all__"
