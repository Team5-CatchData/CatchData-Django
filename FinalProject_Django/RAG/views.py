import json
import os
from datetime import datetime

import google.genai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pgvector.django import CosineDistance

from .models import EmbeddedData

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


@csrf_exempt
@require_http_methods(["POST"])
def rag_chat_api(request):
    """
    RAG 기반 맛집 추천 채팅 API
    """
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "")

        if not user_message:
            return JsonResponse({"error": "메시지가 비어있습니다."}, status=400)

        # 1. 현재 서버 시간 구하기
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        # ---------------------------------------------------------
        # Step 1. Retrieval (검색)
        # ---------------------------------------------------------
        if not client:
            return JsonResponse(
                {"error": "GEMINI_API_KEY가 설정되지 않았습니다."}, status=500
            )

        # 1-1. 사용자 질문 벡터화
        try:
            embedding_response = client.models.embed_content(
                model="text-embedding-004",
                content=user_message,
                task_type="retrieval_query",
            )
            user_embedding = embedding_response["embedding"]
        except Exception as e:
            return JsonResponse(
                {"error": f"임베딩 생성 실패: {str(e)}"}, status=500
            )

        # 1-2. DB 검색
        similar_restaurants = EmbeddedData.objects.annotate(
            distance=CosineDistance("embedding", user_embedding)
        ).order_by("distance")[:10]

        if not similar_restaurants:
            return JsonResponse(
                {"answer": "죄송합니다. 조건에 맞는 맛집을 찾을 수 없습니다."}
            )

        # 1-3. Context 생성
        context_list = []
        recommendations_info = []

        for r in similar_restaurants:
            wait_min = r.estimated_waiting_time

            info = (
                f"- ID: {r.pk}\n"
                f"  이름: {r.name}\n"
                f"  카테고리: {r.category}\n"
                f"  위치: {r.address}\n"
                f"  예상 대기시간: {wait_min}분\n"
                f"  평점: {r.rating}\n"
                f"  특징: {r.description}\n"
            )
            context_list.append(info)
            recommendations_info.append({"restaurant_ID": r.pk, "name": r.name})

        context_text = "\n".join(context_list)

        # ---------------------------------------------------------
        # Step 2. Generation (생성): 프롬프트 엔지니어링
        # ---------------------------------------------------------

        system_instruction = (
            f"당신은 스마트한 맛집 추천 AI입니다.\n"
            f"현재 시각은 **{current_time_str}** 입니다.\n\n"
            "사용자의 질문과 [참고 정보]를 분석하여 최적의 맛집을 "
            "**최소 1개에서 최대 3개까지만** 추천하세요.\n"
            "사용자의 질문이 모호하거나(위치, 음식 종류 누락 등) 정보가 부족해도, "
            "**[참고 정보] 내에서 가장 적절한 곳(평점이 높거나 대기가 적은 곳)을 "
            "스스로 판단**하여 추천해야 합니다.\n\n"
            "**[추천 로직: 시나리오 선택]**\n\n"
            "**시나리오 A: '지금' 또는 '바로' 가고 싶거나, 시간 언급이 없는 경우**\n"
            "1. 사용자는 즉시 입장을 원합니다.\n"
            "2. [참고 정보] 중 **'예상 대기시간'이 가장 짧은(0에 가까운)** 식당을 "
            "우선적으로 선택하세요.\n"
            "3. 대기 시간이 비슷하다면 평점이 높은 곳을 추천하세요.\n\n"
            "**시나리오 B: '미래 시간'(예: 5시, 저녁 등)을 언급한 경우**\n"
            "1. (희망 방문 시간) - (현재 시각) = **'이동 및 대기 가능 시간(Gap)'**을 "
            "계산하세요.\n"
            "   (예: 현재 3시 -> 희망 5시 = 120분 여유)\n"
            "2. [참고 정보] 중 **'예상 대기시간'이 'Gap'과 비슷하거나 그보다 낮은** "
            "식당을 선택하세요.\n"
            "   - **핵심:** 여유 시간이 충분하다면, 대기가 좀 있더라도 인기 있는"
            "(웨이팅이 긴) 맛집을 추천하는 것이 더 좋은 추천일 수 있습니다.\n"
            "   - 예: 120분 여유가 있다면, 대기 100분인 인기 맛집을 1순위로 추천 "
            "(도착 시 바로 입장 가능하므로).\n\n"
            "**[응답 형식 (JSON 포맷 엄수)]**\n"
            "반드시 아래 JSON 형식으로만 응답하세요. 다른 말은 덧붙이지 마세요.\n"
            "{\n"
            '  "restaurant_ID": [추천 식당 ID 리스트 (정수형, 1~3개)],\n'
            '  "answer": "친절한 추천 멘트. 시나리오 A라면 \'지금 바로 입장 가능해서 '
            "추천해요', 시나리오 B라면 '가시는 동안 웨이팅이 빠져 도착 즈음 입장 가능할 "
            "거예요' 등의 구체적 근거 포함.\"\n"
            "}"
        )

        full_prompt = (
            f"{system_instruction}\n\n"
            f"[참고 정보]\n{context_text}\n\n"
            f"사용자 질문: {user_message}"
        )

        try:
            response = client.models.generate_content(
                model="gemini-pro",
                contents=full_prompt,
            )

            response_text = response.text.strip()

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            response_data = json.loads(response_text)

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            backup_ids = [r["restaurant_ID"] for r in recommendations_info[:3]]
            return JsonResponse(
                {"restaurant_ID": backup_ids, "answer": response.text}
            )
        except Exception as e:
            return JsonResponse(
                {"error": f"LLM 생성 오류: {str(e)}"}, status=500
            )

    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
