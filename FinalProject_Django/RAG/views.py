import json
import os

import google.genai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from main.models import ChatHistory

from .services import RagPipelineError, run_rag_pipeline

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

DEFAULT_TOP_K = 30


@csrf_exempt
@require_http_methods(["POST"])
def rag_chat_api(request):
    """
    RAG 기반 맛집 추천 채팅 API
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)

    user_message = data.get("message", "")

    try:
        result = run_rag_pipeline(client, user_message, top_k=DEFAULT_TOP_K)
    except RagPipelineError as e:
        return JsonResponse({"error": str(e)}, status=e.status)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    response_data = {
        "restaurant_ID": result["restaurant_ID"],
        "answer": result["answer"],
    }

    if result["generated"]:
        try:
            ChatHistory.objects.create(
                query=user_message, answer=response_data.get("answer", "")
            )
        except Exception as save_error:
            # 저장 실패해도 응답은 반환
            print(f"채팅 기록 저장 실패: {save_error}")

    return JsonResponse(response_data)
