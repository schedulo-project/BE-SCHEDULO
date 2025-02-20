from django.urls import path
from users import views

app_name = "users"

urlpatterns = [
    path("", views.UserDetailView.as_view(), name="user"),
    path("signup/", views.UserCreateView.as_view(), name="signup"),
    path("checkduplicate/", views.check_duplicate, name="check-duplicate"),
    path("passwordreset/", views.PasswordResetView.as_view(), name="password-reset"),
    path("passwordfind/", views.PasswordFindEmailView.as_view(), name="password-find"),
    path("login/", views.jwt_login_view, name="jwt-login"),
    path("studyroutine/", views.StudyRoutineView.as_view(), name="study"),
]
