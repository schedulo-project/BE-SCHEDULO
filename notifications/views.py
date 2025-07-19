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
