from datetime import datetime
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from schedules.models import Tag, Schedule, TimeTable
from schedules.serializers import (
    TagSerializer,
    ScheduleSerializer,
    GroupedScheduleSerializer,
    TimeTableSerializer,
)
from users.models import User


# Tag 조회, 생성
class TagListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


# Tag 수정, 삭제
class TagRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer
    lookup_field = "id"
    lookup_url_kwarg = "tag_id"

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


# Schedule 생성
class ScheduleListCreateAPIView(generics.CreateAPIView):
    serializer_class = ScheduleSerializer

    def perform_create(self, serializer):
        tag = self.request.data.get("tag")
        if tag:
            tag_instance = Tag.objects.filter(id=int(tag))
        serializer.save(tag=tag_instance, user=self.request.user)

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)


# Schedule 조회
@api_view(["GET"])
def schedules_list_api_view(request):
    first = request.GET.get("first", None)
    last = request.GET.get("last", None)

    if first and last:
        first_date_instance = datetime.strptime(first, "%Y-%m-%d").date()
        last_date_instance = datetime.strptime(last, "%Y-%m-%d").date()
        schedules = Schedule.objects.filter(
            user=request.user,
            scheduled_date__range=[first_date_instance, last_date_instance],
        )
    elif first and not last:
        first_date_instance = datetime.strptime(first, "%Y-%m-%d").date()
        schedules = Schedule.objects.filter(
            user=request.user, scheduled_date=first_date_instance
        )
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupedScheduleSerializer(schedules)
    return Response(serializer.data)


# Schedule 조회 by title
@api_view(["GET"])
def schedules_list_by_title_api_view(request):
    title = request.GET.get("title", None)
    if title:
        schedules = Schedule.objects.filter(user=request.user, title__icontains=title)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    serializer = GroupedScheduleSerializer(schedules)
    print(schedules)
    return Response(serializer.data)


# Schedule 단일 조회, 수정, 삭제
class ScheduleRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScheduleSerializer
    lookup_field = "id"
    lookup_url_kwarg = "schedule_id"

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)


# TimeTable 조회, 생성, 수정
class TimeTableListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TimeTableSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return TimeTable.objects.filter(user=self.request.user)


class TimeTableRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TimeTableSerializer
    lookup_field = "id"
    lookup_url_kwarg = "timetable_id"

    def get_queryset(self):
        return TimeTable.objects.filter(user=self.request.user)
