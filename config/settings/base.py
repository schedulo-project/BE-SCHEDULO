from datetime import timedelta
import json
import os
import environ
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")

ENCRYPTION_KEY = env("ENCRYPTION_KEY")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())


# Application definition

INSTALLED_APPS = [
    # cors
    "corsheaders",
    # contrib
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # drf
    "rest_framework",
    "rest_framework_simplejwt",
    # apps
    "users",
    "schedules",
    "chatbots",
    "notifications",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    )
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=6),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = env("EMAIL")
EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Celery settings
CELERY_BROKER_URL = "redis://127.0.0.1:6379"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379"


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# cors setting
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://localhost:443",
    "http://localhost:5174",
    "http://13.124.140.60:8000",
    "http://13.124.140.60:5173",
    "http://13.124.140.60:443",
    "http://13.124.140.60:5174",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:443",
    "http://127.0.0.1:5174",
]
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),  # 정적 파일 경로 설정
]

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "score-api": {
        "task": "users.tasks.update_user_score",
        "schedule": crontab(hour=0, minute=30),  # 매일 00시 30분에 실행
    },
    "notify_today_schedule_morning": {
        "task": "notifications.tasks.notify_today_schedule",
        "schedule": crontab(hour=10, minute=0),  # 매일 10시 00분에 실행
        "args": ("📅 오늘의 일정입니다 :)",),
    },
    "notify_today_schedule_night": {
        "task": "notifications.tasks.notify_today_schedule",
        "schedule": crontab(hour=20, minute=0),  # 매일 20시 00분에 실행
        "args": ("📅 오늘 남은 일정을 확인하세요!",),
    },
    "notify_deadline_schedule": {
        "task": "notifications.tasks.notify_deadline_schedule",
        "schedule": crontab(hour=22, minute=0),  # 매일 10시 00분에 실행
    },
}


# Celery Broker Settings
CELERY_BROKER_URL = "redis://127.0.0.1:6379"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379"


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # 기존 로거 비활성화하지 않음(활성화)
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    # format 설정
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "style": "%",
        },
    },
    "handlers": {
        # 콘솔 핸들러
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        # Django 서버 로그
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        # 이메일로 관리자에게 오류 전송
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        # 파일 핸들러 (5MB 크기 제한, 백업 5개)
        "file": {
            "level": "DEBUG",
            "encoding": "utf-8",
            "filters": ["require_debug_false"],
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/django.log",
            "maxBytes": 1024 * 1024 * 5,  # 로그 크기 제한: 5 MB
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "loggers": {
        # Django 기본 로깅 설정
        "django": {
            "handlers": ["console", "file", "mail_admins"],
            "level": "INFO",
            "propagate": True,  # 상위 로거로 전파
        },
        # Django 서버 로깅
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,  # 상위 로거로 전파 X
        },
        # 사용자 정의 로깅
        "schedulo": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
