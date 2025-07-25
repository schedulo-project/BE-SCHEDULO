from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status


@api_view(["POST"])
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
    return Response(
        {"message": "FCM token updated successfully"}, status=status.HTTP_200_OK
    )


from rest_framework.views import APIView
from firebase_admin import messaging


class FCMTestView(APIView):
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
