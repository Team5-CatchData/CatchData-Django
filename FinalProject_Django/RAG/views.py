import json
import os

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pgvector.django import CosineDistance

from .models import EmbeddedData

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


@csrf_exempt
@require_http_methods(["POST"])
def rag_chat_api(request):
    """
    RAG 기반 맛집 추천 채팅 API
    1. 사용자 질문을 벡터화
    2. DB에서 코사인 유사도로 가장 가까운 맛집 검색
    3. 대기 시간(팀당 10분) 계산 후 컨텍스트 생성
    4. LLM에 JSON 포맷으로 답변 요청 및 반환
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')

        if not user_message:
            return JsonResponse({'error': '메시지가 비어있습니다.'}, status=400)

        # ---------------------------------------------------------
        # 1. Retrieval (검색): 사용자 질문과 관련된 맛집 찾기
        # ---------------------------------------------------------

        # 1-1. 사용자 질문을 벡터로 변환
        try:
            embedding_response = genai.embed_content(
                model="models/text-embedding-004",
                content=user_message,
                task_type="retrieval_query"
            )
            user_embedding = embedding_response['embedding']
        except Exception as e:
            return JsonResponse({'error': f'임베딩 생성 실패: {str(e)}'}, status=500)

        # 1-2. DB에서 유사한 맛집 검색 (Cosine Distance 이용)
        similar_restaurants = EmbeddedData.objects.annotate(
            distance=CosineDistance('embedding', user_embedding)
        ).order_by('distance')[:4]  # 상위 4개 추출

        # 1-3. 검색된 맛집 정보를 텍스트로 정리 (Context 생성) 및 대기 시간 계산
        context_list = []
        recommendations_info = []  # 만약 LLM 파싱 실패 시 사용할 백업 데이터

        for r in similar_restaurants:
            res_id = r.pk

            # 대기 시간 계산: 1팀당 10분
            waiting_count = r.current_waiting_team
            estimated_minutes = waiting_count * 10

            if waiting_count > 0:
                waiting_str = (
                    f"{waiting_count}팀 대기 중 (약 {estimated_minutes}분 소요)"
                )
            else:
                waiting_str = "대기 없음 (바로 입장 가능)"

            info = (
                f"- ID: {res_id}\n"
                f"  이름: {r.name}\n"
                f"  카테고리: {r.category}\n"
                f"  주소: {r.address}\n"
                f"  대기 현황: {waiting_str}\n"
                f"  특징: {r.description}\n"
                f"  평점: {r.rating}\n"
            )
            context_list.append(info)

            recommendations_info.append({
                'restaurant_ID': res_id,
                'name': r.name
            })

        if context_list:
            context_text = "\n\n".join(context_list)
        else:
            context_text = "관련된 맛집 정보가 없습니다."

        # ---------------------------------------------------------
        # 2. Generation (생성): LLM에게 JSON 응답 요청
        # ---------------------------------------------------------

        system_instruction = (
            "당신은 맛집 추천 전문가입니다. 아래 [참고 정보]를 바탕으로 사용자 질문에 답변해주세요.\n"
            "**반드시 아래의 JSON 형식으로만 응답해야 합니다. 다른 말은 덧붙이지 마세요.**\n\n"
            "응답 예시:\n"
            "{\n"
            '  "restaurant_ID": [123, 456],\n'
            '  "answer": "홍대 근처라면 00식당을 추천해요! '
            '현재 대기가 2팀 있어 약 20분 기다려야 합니다."\n'
            "}\n\n"
            "지침:\n"
            "- 'restaurant_ID' 리스트에는 [참고 정보]에 있는 식당 중 추천하는 곳의 'ID'를 "
            "정수형으로 담으세요.\n"
            "- 'answer'에는 [참고 정보]의 '대기 현황'과 '예상 대기 시간'을 포함하여 "
            "구체적으로 설명하세요.\n"
            "- [참고 정보]에 없는 내용은 지어내지 마세요.\n"
        )

        full_prompt = (
            f"{system_instruction}\n\n[참고 정보]\n{context_text}\n\n"
            f"사용자 질문: {user_message}"
        )

        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(full_prompt)

            response_text = response.text
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
            # LLM이 JSON 형식을 지키지 않았을 때 백업 응답
            return JsonResponse({
                'restaurant_ID': [r['restaurant_ID'] for r in recommendations_info],
                'answer': response.text
            })
        except Exception as e:
            return JsonResponse({'error': f'LLM 생성 오류: {str(e)}'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
