from django.urls import path
from users import views
from users import crawling
from rest_framework_simplejwt.views import TokenRefreshView


app_name = "users"

urlpatterns = [
    ### user info ###
    path("", views.UserDetailView.as_view(), name="user"),
    path("signup/", views.UserCreateView.as_view(), name="signup"),
    path("checkduplicate/", views.check_duplicate, name="check-duplicate"),
    # path("passwordreset/", views.PasswordResetView.as_view(), name="password-reset"),
    path("pw/check/", views.PasswordCheckView.as_view(), name="password-check"),
    path("pw/update/", views.PasswordUpdateView.as_view(), name="password-update"),
    path("passwordfind/", views.PasswordFindEmailView.as_view(), name="password-find"),
    path("smul-update/", views.SmulPasswordUpdateView.as_view(), name="smul-update"),
    ### jwt login ###
    path("login/", views.JWTLoginView.as_view(), name="jwt-login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    ### study routine ###
    path("studyroutine/", views.StudyRoutineView.as_view(), name="study"),
    ### crawling ###
    path(
        "studentinfocheck/",
        crawling.StudentInfoCheckView.as_view(),
        name="student-info-check",
    ),
    path("crawling/", crawling.CrawlingView.as_view(), name="crawling"),
    path("getTimeTable/", crawling.GetTimeTableView.as_view(), name="get-time-table"),
    path(
        "timetable/status/",
        crawling.TimeTableTaskStatusView.as_view(),
        name="timetable-task-status",
    ),
    ### score ###
    path("scores/", views.get_user_score, name="get-user-score"),
]
