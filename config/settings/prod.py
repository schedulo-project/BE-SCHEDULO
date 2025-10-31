from .base import *

DEBUG = False

ALLOWED_HOSTS = ["*"]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="schedulo_db"),
        "USER": env("DB_USER", default="schedulo_user"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="db"),   # ← 서비스명 'db'
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        },
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}

# Celery Beat 파일 경로
CELERY_BEAT_SCHEDULE_FILENAME = os.path.join(BASE_DIR, "data", "celerybeat-schedule")
