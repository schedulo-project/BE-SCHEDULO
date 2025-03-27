from django.urls import path

from schedules import views

urlpatterns = [
    # Tag
    path("tags/", views.TagListCreateAPIView.as_view()),
    path("tags/<int:tag_id>/", views.TagRetrieveUpdateDestroyAPIView.as_view()),
    # Schedule
    path("", views.ScheduleListCreateAPIView.as_view()),
    path("<int:schedule_id>/", views.ScheduleRetrieveUpdateDestroyAPIView.as_view()),
    path("list/", views.schedules_list_api_view),
    path("list/title/", views.schedules_list_by_title_api_view),
    # TimeTable
    path("timetables/", views.TimeTableListCreateAPIView.as_view()),
    path(
        "timetables/<int:timetable_id>/",
        views.TimeTableRetrieveUpdateDestroyAPIView.as_view(),
    ),
]
