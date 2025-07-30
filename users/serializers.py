from users.models import StudyRoutine, User
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


class UserSerializer(serializers.ModelSerializer):
    student_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["email", "password", "student_id", "student_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create(email=validated_data["email"])
        user.set_password(validated_data["password"])

        if "student_id" in validated_data:
            user.student_id = validated_data["student_id"]
        if "student_password" in validated_data:
            user.set_student_password(validated_data["student_password"])
        user.save()
        return user


class JWTLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"message": "존재하지 않는 계정입니다."})

        if not user.check_password(password):
            raise serializers.ValidationError({"message": "비밀번호가 옳지 않습니다."})

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return {
            "refresh": str(refresh),
            "access": str(access),
            "id": user.id,
            "email": user.email,
        }


class StudyRoutineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyRoutine
        fields = ["weeks_before_exam", "review_type", "user"]
