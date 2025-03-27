from users.models import StudyRoutine, User
from rest_framework import serializers
from django.contrib.auth.forms import PasswordResetForm


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


class StudyRoutineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyRoutine
        fields = ["weeks_before_exam", "review_type", "user"]
