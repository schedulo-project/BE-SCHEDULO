from .base import *

DEBUG = False

ALLOWED_HOSTS = ["*"]

# Database
DB_PASSWORD = env("DB_PASSWORD")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "schedulo",
        "USER": "root",
        "PASSWORD": DB_PASSWORD,
        "HOST": "13.124.140.60",
        "PORT": "3306",
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Celery Beat 스케줄 파일 경로 수정 (프로덕션용)
CELERY_BEAT_SCHEDULE_FILENAME = "/home/ubuntu/BE-MVP/data/celerybeat-schedule"
