from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser

from config import settings
from users.managers import CustomUserManager
from django.utils.translation import gettext_lazy as _

from cryptography.fernet import Fernet

cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode())


class User(AbstractUser):
    username, first_name, last_name = None, None, None
    email = models.EmailField(_("email address"), unique=True)
    student_id = models.IntegerField(null=True, unique=True)
    student_password = models.BinaryField(null=True, blank=True)  # encrypted password

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def set_student_password(self, raw_password):
        """AES encrypt student password"""
        try:
            if raw_password:
                encrypted_password = cipher_suite.encrypt(raw_password.encode())
                self.student_password = encrypted_password
        except Exception as e:
            raise ValueError(f"Password encryption failed: {str(e)}")

    def get_student_password(self):
        """AES decrypt student password"""
        try:
            if self.student_password:
                return cipher_suite.decrypt(self.student_password).decode()
            return None
        except Exception as e:
            raise ValueError(f"Password decryption failed: {str(e)}")

    def __str__(self):
        return self.email


class StudyRoutine(models.Model):
    weeks_before_exam = models.IntegerField(null=True)
    review_type = models.CharField(null=True, max_length=30)
    user = models.ForeignKey(
        User, null=True, on_delete=models.CASCADE, related_name="study_routine"
    )
