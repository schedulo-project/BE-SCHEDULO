from users.models import StudyRoutine, User
from rest_framework import serializers
from django.contrib.auth.forms import PasswordResetForm

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'username']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class StudyRoutineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyRoutine
        fields = ['weeks_before_exam', 'review_type', 'user']