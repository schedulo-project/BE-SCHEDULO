from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status, permissions

from notifications.models import WebPushSubscription
from notifications.serializers import (
    NotificationSettingSerializer,
    SubscriptionSerializer,
)
from rest_framework import generics, permissions

from notifications.utils import send_multi_channel
from users.models import User


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_fcm_token(request):
    fcm_token = request.data.get("fcm_token")

    if not fcm_token:
        return Response(
            {"error": "fcm_token is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user
    if user.fcm_token != fcm_token:
        user.fcm_token = fcm_token
        user.save(update_fields=["fcm_token"])
        print(f"FCM 토큰 업데이트 완료: 사용자 {user.email}, 토큰: {fcm_token[:20]}...")
    else:
        print(f"FCM 토큰이 이미 동일합니다: 사용자 {user.email}")

    return Response(
        {"message": "FCM token updated successfully"}, status=status.HTTP_200_OK
    )


from rest_framework.views import APIView
from firebase_admin import messaging


class PushTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        title = request.data.get("title", "테스트")
        body = request.data.get("body", "푸시알림 테스트")
        try:
            send_multi_channel(request.user, title, body, url="/")
            return Response({"message": "전송 시도 완료"}, status=200)
        except Exception as e:
            return Response({"message": "전송 실패", "error": str(e)}, status=500)


class FCMTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        fcm_token = request.user.fcm_token
        title = request.data.get("title", "test alert")
        body = request.data.get("body", "푸시알림 테스트")

        if not fcm_token:
            return Response(
                {"error": "fcm_token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=fcm_token,
        )

        try:
            response = messaging.send(message)
            return Response(
                {
                    "message": "푸시 알림이 성공적으로 전송되었습니다.",
                    "response": response,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": "푸시 알림 전송 실패", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationSettingsUpdateView(generics.UpdateAPIView):
    serializer_class = NotificationSettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user


class SubscribeView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]  # 로그인 매핑 원하면 IsAuthenticated
    serializer_class = SubscriptionSerializer


class UnsubscribeView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, *args, **kwargs):
        endpoint = request.data.get("endpoint") or request.query_params.get("endpoint")
        if not endpoint:
            return Response(
                {"detail": "endpoint required"}, status=status.HTTP_400_BAD_REQUEST
            )
        WebPushSubscription.objects.filter(endpoint=endpoint).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
