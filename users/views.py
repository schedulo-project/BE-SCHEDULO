from django.shortcuts import render
from users.models import StudyRoutine, User
from users.serializers import StudyRoutineSerializer, UserSerializer
from django.contrib.auth.hashers import check_password
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.crypto import get_random_string
from django.core.mail import EmailMessage


# User 관련 view


# 조회, 탈퇴
class UserDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
