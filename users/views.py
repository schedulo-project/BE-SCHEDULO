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
