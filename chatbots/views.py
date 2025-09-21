import json
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Chatting
from .serializers import ChattingSerializer
from .graphs import run_agent_graph

from django.utils import timezone


from .core_agent import run_core_agent


class ChatbotAPIView(APIView):
    def get(self, request):
        chattings = Chatting.objects.filter(user=request.user).order_by("-created_at")
        serializer = ChattingSerializer(chattings, many=True)
        return Response(serializer.data)

    def post(self, request):
        query = request.data.get("query")
        answer = run_agent_graph(query, request.user.id)

        return Response(answer)
