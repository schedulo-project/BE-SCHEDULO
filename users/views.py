import logging
from django.shortcuts import render
from users.models import StudyRoutine, User, Score
from users.serializers import (
    JWTLoginSerializer,
    StudyRoutineSerializer,
    UserSerializer,
    UserSmulUpdateSerializer,
)
from django.contrib.auth.hashers import check_password
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.crypto import get_random_string
from django.core.mail import EmailMessage


# User 관련 view
logger = logging.getLogger("schedulo")


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
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"가입된 사용자 정보: {user.email}")

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "회원가입이 완료되었습니다.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "student_id": user.student_id if user.student_id else None,
                },
            },
            status=status.HTTP_201_CREATED,
        )


# 이캠 정보 수정
class SmulPasswordUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSmulUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": " 샘물 로그인 정보가 수정되었습니다.",
            },
            status=status.HTTP_200_OK,
        )


# 중복 확인(이메일, 아이디)
@api_view(["POST"])
@permission_classes([AllowAny])
def check_duplicate(request):
    fields = [("email", "이메일"), ("student_id", "아이디")]

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


# 비밀번호 확인
class PasswordCheckView(APIView):
    def post(self, request):
        password = request.data.get("current_password")
        if not check_password(password, request.user.password):
            return Response(
                {"message": "잘못된 비밀번호입니다."}, status=status.HTTP_404_NOT_FOUND
            )
        else:
            return Response(
                {"message": "올바른 비밀번호입니다."}, status=status.HTTP_200_OK
            )


# 비밀번호 변경
class PasswordUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        new_password = request.data.get("new_password")
        user = request.user

        if check_password(new_password, user.password):
            return Response(
                {"message": "이전 비밀번호는 사용할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            user.set_password(new_password)
            user.save()
            return Response(
                {"message": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK
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


# JWT 토큰 발급(로그인)
class JWTLoginView(GenericAPIView):
    serializer_class = JWTLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = Response(
            {
                "access": serializer.validated_data["access"],
                "refresh": serializer.validated_data["refresh"],
                "user": {
                    "id": serializer.validated_data["id"],
                    "email": serializer.validated_data["email"],
                },
            },
            status=status.HTTP_200_OK,
        )
        return response


# StudyRoutine 관련 view
# 1. 공부 계획 등록
# 2. 공부 계획 수정
class StudyRoutineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        study_routine = StudyRoutine.objects.filter(user=request.user).first()
        if study_routine:
            serializer = StudyRoutineSerializer(study_routine)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        if StudyRoutine.objects.filter(user=request.user).exists():
            study_routine = StudyRoutine.objects.get(user=request.user)
            serializer = StudyRoutineSerializer(
                study_routine, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = StudyRoutineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


from datetime import date, timedelta


# 유저 스코어 관련 view
@api_view(["GET"])
def get_user_score(request):
    if request.user.is_authenticated:
        # Mock data
        if request.GET.get("mock"):
            data = [
                {"x": "03월 01일", "y": 100},
                {"x": "03월 02일", "y": 90},
                {"x": "03월 03일", "y": 95},
                {"x": "03월 04일", "y": 110},
                {"x": "03월 05일", "y": 110},
                {"x": "03월 06일", "y": 115},
                {"x": "03월 07일", "y": 120},
            ]
            return Response(
                {"data": data, "highest": 178, "percentage": 32},
                status=status.HTTP_200_OK,
            )
        user = request.user
        scores = user.scores
        iter = 0
        data = []
        if scores.exists():
            # 반복 횟수 설정 (최대 7)
            if scores.count() < 7:
                iter = scores.count()
            else:
                iter = 7
            # 반복 횟수만큼 데이터로 변환
            for i in range(iter):
                score = scores.filter(
                    date=(date.today() - timedelta(days=iter - i - 1))
                ).first()
                data.append(
                    {
                        "x": score.date.strftime("%m월 %d일"),
                        "y": score.score,
                    }
                )
            return Response(
                {
                    "data": data,
                    "highest": scores.first().highest,
                    "percentage": scores.first().percentage,
                },
                status=status.HTTP_200_OK,
            )
        # 스코어가 없는 경우 (e.g. 오늘 가입)
        else:
            data.append({"x": date.today().strftime("%m월 %d일"), "y": 100})
            return Response(
                {"data": data, "highest": 100, "percentage": 100.0},
                status=status.HTTP_200_OK,
            )
    return Response(status=status.HTTP_401_UNAUTHORIZED)
