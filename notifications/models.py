from django.db import models
from django.conf import settings


class WebPushSubscription(models.Model):
    """
    Web Push 알림을 위한 구독 정보를 저장하는 모델
    FCM을 지원하지 않는 브라우저(예: Safari)에서 사용
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="webpush_subscriptions",
        verbose_name="사용자",
    )
    endpoint = models.URLField(
        unique=True,
        verbose_name="구독 엔드포인트",
        help_text="Web Push 서비스의 구독 엔드포인트 URL",
    )
    p256dh = models.TextField(
        verbose_name="P-256 DH 공개키",
        help_text="Web Push 암호화를 위한 P-256 DH 공개키",
    )
    auth = models.CharField(
        max_length=200, verbose_name="인증 키", help_text="Web Push 인증을 위한 키"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        verbose_name = "Web Push 구독"
        verbose_name_plural = "Web Push 구독들"
        indexes = [models.Index(fields=["user"])]
        ordering = ["-created_at"]

    def __str__(self):
        return self.endpoint[:64]

    @property
    def is_active(self):
        """구독이 활성 상태인지 확인"""
        return bool(self.endpoint and self.p256dh and self.auth)
