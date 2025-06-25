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
