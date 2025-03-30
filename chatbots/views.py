import json
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Chatting
from .serializers import ChattingSerializer
from .services import get_chatbot_response


class ChatbotAPIView(APIView):
    def get(self, request):
        chattings = Chatting.objects.filter(user=request.user).order_by("-created_at")
        serializer = ChattingSerializer(chattings, many=True)
        return Response(serializer.data)

    def post(self, request):
        query = request.data.get("query")
        answer_json = get_chatbot_response(query)[7:-4]
        answer_dict = json.loads(answer_json)

        chatting = Chatting.objects.create(
            query=query, answer=answer_dict, user=request.user
        )

        serializer = ChattingSerializer(chatting)
        return Response(serializer.data)
