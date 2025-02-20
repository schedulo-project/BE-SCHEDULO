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


# 회원가입
class UserCreateView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserSerializer


# 중복 확인(이메일, 아이디)
@api_view(["POST"])
@permission_classes([AllowAny])
def check_duplicate(request):
    fields = [("email", "이메일"), ("username", "아이디")]

    for field_key, display_name in fields:
        value = request.data.get(field_key)
        if value:
            if User.objects.filter(**{field_key: value}).exists():
                return Response(
                    {"message": f"이미 사용 중인 {display_name}입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"message": f"사용 가능한 {display_name}입니다."},
                status=status.HTTP_200_OK,
            )

    return Response(
        {"message": "잘못된 요청입니다."}, status=status.HTTP_400_BAD_REQUEST
    )


