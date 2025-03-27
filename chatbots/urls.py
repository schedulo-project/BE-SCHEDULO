from django.urls import path

from chatbots import views

urlpatterns = [
    path("", views.ChatbotAPIView.as_view()),
]
