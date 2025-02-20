from rest_framework.response import Response
from rest_framework import generics

from schedules.models import Tag, Schedule, TimeTable
from schedules.serializers import TagSerializer, ScheduleSerializer, TimeTableSerializer

# Tag 조회, 생성
class TagListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)
        
# Tag 수정, 삭제
class TagRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'tag_id'

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

# Schedule 조회(캘린더 고려), 생성
class ScheduleListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)
    
# Schedule 수정, 삭제, 연기
class ScheduleRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ScheduleSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'schedule_id'

    def get_queryset(self):
        return Schedule.objects.filter(user=self.request.user)

# TimeTable 조회, 생성, 수정