import json
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Chatting
from .serializers import ChattingSerializer, AnswerSerializer
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
        answer_serializer = AnswerSerializer(data=answer_dict)
        answer_serializer.is_valid(raise_exception=True)
        answer = answer_serializer.save()

        chatting = Chatting.objects.create(
            query=query, answer=answer, user=request.user
        )

        serializer = ChattingSerializer(chatting)
        return Response(serializer.data)
