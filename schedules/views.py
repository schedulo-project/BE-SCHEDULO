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

tag_colors = [
    "#CFE6D6",
    "#FFEDA4",
    "#FDD0EB",
    "#E0CFE6",
    "#BDC49E",
    "#F7D5AB",
    "#C3E1FF",
    "#D9D4C1",
    "#F5CDCD",
]


# Tag 조회, 생성
class TagListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if Tag.objects.filter(
            name=request.data.get("name"), user=request.user
        ).exists():
            return Response(status=status.HTTP_200_OK)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        order = Tag.objects.filter(user=self.request.user).count()
        serializer.save(
            user=self.request.user, color=tag_colors[order % len(tag_colors)]
        )

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
class ScheduleCreateAPIView(generics.CreateAPIView):
    serializer_class = ScheduleSerializer

    def create(self, request):
        data = request.data
        tag = data.get("tag", [])

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            schedule = serializer.save(user=request.user)
            tag_instances = []
            for tag_name in tag:
                tag_instance, created = Tag.objects.get_or_create(
                    name=tag_name, user=request.user
                )
                if created:
                    order = Tag.objects.filter(user=self.request.user).count()
                    tag_instance.color = tag_colors[order % len(tag_colors)]
                    tag_instance.save()
                tag_instances.append(tag_instance)
            schedule.tag.set(tag_instances)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        ids = request.data.get("ids", None)
        if not ids:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        schedules = Schedule.objects.filter(id__in=ids, user=request.user)
        if schedules.exists():
            schedules.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)


# Schedule 다중 생성
class ScheduleBulkCreateAPIView(generics.CreateAPIView):
    serializer_class = ScheduleSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Schedule 조회
@api_view(["GET"])
def schedules_list_api_view(request):
    first = request.GET.get("first", None)
    last = request.GET.get("last", None)
    title = request.GET.get("title", None)
    tag = request.GET.get("tag", None)

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

    if not schedules.exists():
        return Response(data={"schedules": {}}, status=status.HTTP_204_NO_CONTENT)

    if title:
        schedules = schedules.filter(title__icontains=title)
    if tag:
        schedules = schedules.filter(tag__name=tag)

    serializer = GroupedScheduleSerializer(schedules)
    delayed_schedules = schedules.filter(
        scheduled_date__lt=datetime.now().date(), is_completed=False
    )
    delayed_serializer = ScheduleSerializer(delayed_schedules, many=True)
    data = serializer.data
    data["delayed_schedules"] = delayed_serializer.data
    return Response(data)


# Schedule 단일 조회, 수정, 삭제
class ScheduleRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScheduleSerializer
    lookup_field = "id"
    lookup_url_kwarg = "schedule_id"

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        tag = data.get("tag", [])

        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            schedule = serializer.save(user=request.user)
            tag_instances = []
            for tag_name in tag:
                tag_instance, created = Tag.objects.get_or_create(
                    name=tag_name, user=request.user
                )
                if created:
                    order = Tag.objects.filter(user=self.request.user).count()
                    tag_instance.color = tag_colors[order % len(tag_colors)]
                    tag_instance.save()
                tag_instances.append(tag_instance)
            schedule.tag.set(tag_instances)

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)


@api_view(["DELETE"])
def schedule_delete_api_view(request):
    ids = request.data.get("ids", None)
    schedules = Schedule.objects.filter(id__in=ids, user=request.user)
    if schedules.exists():
        schedules.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


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
