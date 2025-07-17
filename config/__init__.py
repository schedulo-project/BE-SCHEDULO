from .celery import app as celery_app

__all__ = ("celery_app",)

# Firebase 초기화
import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
