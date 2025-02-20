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


# 비밀번호 찾기
class PasswordFindEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if "email" in request.data:
            email = request.data.get("email")
            if not email:
                return Response(
                    {"message": "이메일을 입력해주세요."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif not User.objects.filter(email=email).exists():
                return Response(
                    {"message": "존재하지 않는 이메일입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            verification_code = get_random_string(length=8, allowed_chars="1234567890")
            message = f"인증번호는 {verification_code}입니다."
            email_message = EmailMessage(
                subject="비밀번호 찾기 인증번호", body=message, to=[email]
            )
            email_message.send()
            # 인증번호를 세션에 저장
            request.session["email"] = email
            request.session["verification_code"] = verification_code
            request.session.set_expiry(180)  # 인증번호 유효시간 3분
            return Response(
                {
                    "message": "비밀번호 변경 인증번호 전송",
                    "verification_code": verification_code,
                },
                status=status.HTTP_200_OK,
            )

        elif "verification_code" in request.data:
            verification_code = request.data.get("verification_code")
            if verification_code != request.session.get("verification_code"):
                request.session.flush()
                return Response(
                    {"message": "인증번호가 옳지 않습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            request.session["verified"] = True
            return Response(
                {"message": "인증번호가 확인되었습니다."}, status=status.HTTP_200_OK
            )

        elif "password" in request.data:
            if request.session.get("verified"):
                email = request.session.get("email")
                user = User.objects.get(email=email)
                user.set_password(request.data.get("password"))
                user.save()
                request.session.flush()
                return Response(
                    {"message": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "인증번호가 확인되지 않았습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"message": "잘못된 요청입니다."}, status=status.HTTP_400_BAD_REQUEST
        )


# 로그인
@api_view(["POST"])
@permission_classes([AllowAny])
def jwt_login_view(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if not User.objects.filter(email=email).exists():
        return Response(
            {"message": "존재하지 않는 계정입니다."}, status=status.HTTP_400_BAD_REQUEST
        )
    user = User.objects.get(email=email)
    if not check_password(password, user.password):
        return Response(
            {"message": "비밀번호가 옳지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    token = RefreshToken.for_user(user)
    serializer = UserSerializer(user)
    return Response(
        status=status.HTTP_200_OK,
        data={
            "token": str(token.access_token),
            "user": serializer.data,
        },
    )
