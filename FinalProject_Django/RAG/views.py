import json
import os
from datetime import datetime

import google.genai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from google.genai import types
from main.models import ChatHistory
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
                contents=user_message,
                config=types.EmbedContentConfig(
                    task_type="retrieval_query",
                ),
            )
            user_embedding = embedding_response.embeddings[0].values

        except Exception as e:
            return JsonResponse(
                {"error": f"임베딩 생성 실패: {str(e)}"}, status=500
            )

        # 1-2. DB 검색
        similar_restaurants = EmbeddedData.objects.annotate(
            distance=CosineDistance("embedding", user_embedding)
        ).order_by("distance")[:30]

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
                f"- ID: {r.place_id}\n"
                f"  이름: {r.name}\n"
                f"  카테고리: {r.category}\n"
                f"  위치: {r.address}\n"
                f"  예상 대기시간: {wait_min}분\n"
                f"  평점: {r.rating}\n"
                f"  특징: {r.description}\n"
            )
            context_list.append(info)
            recommendations_info.append({"restaurant_ID": r.place_id, "name": r.name})

        context_text = "\n".join(context_list)

        # ---------------------------------------------------------
        # Step 2. Generation (생성): 프롬프트 엔지니어링
        # ---------------------------------------------------------

        system_instruction = (
            f"당신은 '효율'과 '미식'의 균형을 완벽하게 맞추는 "
            f"스마트 맛집 가이드입니다.\n"
            f"현재 시각은 **{current_time_str}** 입니다.\n\n"

            "사용자의 질문과 [참고 정보]를 분석하여 최적의 맛집을 "
            "**최소 1개에서 최대 3개까지만** 추천하세요.\n"
            "기본 우선순위는 **'대기시간 >= 카테고리 >= 평점'**이지만, "
            "기계적인 판단이 아닌 유연한 추천을 해야 합니다.\n\n"

            "**[핵심 판단 기준: '10분의 미학']**\n"
            "1. **대기 시간 (Primary):** "
            "기본적으로 대기 시간이 짧을수록 좋습니다. "
            "하지만 '0분'만 고집하지 마세요.\n"
            "2. **가치 판단 (The Trade-off):** "
            "**대기 시간이 10분 내외(5~15분)**라면, "
            "평점을 확인하세요.\n"
            "   - **Case A:** "
            "대기 0분, 평점 3.5점 vs **대기 10분, 평점 4.5점**\n"
            "     -> **후자(대기 10분)를 강력 추천하세요.** "
            "10분은 맛있는 음식을 위해 충분히 투자할 만한 시간입니다.\n"
            "   - **Case B:** "
            "대기 0분, 평점 4.0점 vs 대기 10분, 평점 4.1점\n"
            "     -> **전자(대기 0분)를 추천하세요.** "
            "평점 차이가 크지 않다면 빠른 입장이 낫습니다.\n"
            "3. **카테고리 (Filter):** "
            "위 시간/평점 비교는 사용자가 원하는 메뉴(카테고리) 내에서 "
            "이루어져야 합니다. 엉뚱한 메뉴를 추천하지 마세요.\n\n"

            "**[추천 시나리오 로직]**\n\n"
            "**시나리오 A: '지금', '바로' 식사 희망**\n"
            "   - 1순위: 대기 없음(0분) + 고평점(4.0 이상)인 완벽한 곳.\n"
            "   - 2순위: **대기 약간(10분 내외) + "
            "초고평점(4.5 이상)인 '기다릴 가치가 있는 곳'.**\n"
            "   - 3순위: 대기 없음 + 평점 무난(3.0 후반).\n"
            "   - **주의:** 대기가 30분 이상 넘어가는 곳은 "
            "사용자가 특별히 '유명한 곳'을 찾지 않는 한 "
            "후순위로 미루세요.\n\n"

            "**시나리오 B: '미래 시간'(예: 6시) 언급**\n"
            "   - 도착 시점 기준, **'바로 입장'** 또는 "
            "**'10분 이내 대기'**가 예상되는 곳을 찾으세요.\n"
            "   - 여유 시간이 넉넉하다면, "
            "평소 웨이팅이 있는 인기 맛집을 추천하며 "
            "'가시는 동안 대기가 빠져서 금방 들어가실 수 있을 거예요'"
            "라고 제안하세요.\n\n"

            "**[응답 형식 (JSON 포맷 엄수)]**\n"
            "반드시 아래 JSON 형식으로만 응답하세요. "
            "다른 말은 덧붙이지 마세요.\n"
            "{\n"
            '  "restaurant_ID": [추천 식당 ID 리스트 (정수형, 1~3개)],\n'
            '  "answer": "합리적인 추천 멘트. '
            "선정 이유를 설득력 있게 설명할 것. "
            "(예: '이곳은 10분 정도 대기가 있지만, "
            "평점이 4.8로 워낙 좋아 기다리실 만한 가치가 있어 "
            "1순위로 추천드려요!' 또는 "
            "'배고프실 텐데 바로 입장 가능한 이곳은 어떠세요?').\"\n"
            "}"
        )

        full_prompt = (
            f"{system_instruction}\n\n"
            f"[참고 정보]\n{context_text}\n\n"
            f"사용자 질문: {user_message}"
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
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

            # 채팅 기록 저장
            try:
                ChatHistory.objects.create(
                    query=user_message,
                    answer=response_data.get('answer', '')
                )
            except Exception as save_error:
                # 저장 실패해도 응답은 반환
                print(f"채팅 기록 저장 실패: {save_error}")

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            backup_ids = [r["restaurant_ID"] for r in recommendations_info[:3]]
            backup_response = {"restaurant_ID": backup_ids, "answer": response.text}

            # 채팅 기록 저장
            try:
                ChatHistory.objects.create(
                    query=user_message,
                    answer=backup_response.get('answer', '')
                )
            except Exception as save_error:
                print(f"채팅 기록 저장 실패: {save_error}")

            return JsonResponse(backup_response)
        except Exception as e:
            return JsonResponse(
                {"error": f"LLM 생성 오류: {str(e)}"}, status=500
            )

    except json.JSONDecodeError:
        return JsonResponse({"error": "잘못된 요청 형식입니다."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
