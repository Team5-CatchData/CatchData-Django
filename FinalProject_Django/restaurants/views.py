import json
import os
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from pgvector.django import CosineDistance

from .models import Restaurant

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
    3. 검색 결과를 컨텍스트로 LLM에 전달하여 답변 생성
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        if not user_message:
            return JsonResponse({'error': '메시지가 비어있습니다.'}, status=400)

        # ---------------------------------------------------------
        # 1. Retrieval (검색): 사용자 질문과 관련된 맛집 찾기
        # ---------------------------------------------------------
        context_text = ""
        similar_restaurants = []
        
        try:
            # 1-1. 사용자 질문을 벡터로 변환
            embedding_response = genai.embed_content(
                model="models/text-embedding-004",
                content=user_message,
                task_type="retrieval_query"
            )
            user_embedding = embedding_response['embedding']

            # 1-2. DB에서 유사한 맛집 검색 (Cosine Distance 이용)
            # embedding 필드와 사용자 질문 벡터 간의 거리를 계산하여 정렬
            similar_restaurants = Restaurant.objects.annotate(
                distance=CosineDistance('embedding', user_embedding)
            ).order_by('distance')[:4]  # 상위 4개 추출

            # 1-3. 검색된 맛집 정보를 텍스트로 정리 (Context 생성)
            context_list = []
            for r in similar_restaurants:
                info = (
                    f"- 이름: {r.name}\n"
                    f"  카테고리: {r.category}\n"
                    f"  주소: {r.address}\n"
                    f"  설명: {r.description}\n"
                    f"  평점: {r.rating} (리뷰 {r.review_count}개)"
                )
                context_list.append(info)
            
            if context_list:
                context_text = "\n\n".join(context_list)

        except Exception as e:
            print(f"RAG 검색 단계 오류: {e}")
            # 검색 실패 시에도 대화는 진행할 수 있도록 처리 (컨텍스트 없이)

        # ---------------------------------------------------------
        # 2. Generation (생성): LLM에게 질문 + 정보 전달
        # ---------------------------------------------------------
        
        system_instruction = (
            "당신은 맛집 추천 전문가입니다. 아래 [참고 정보]에 있는 맛집들을 바탕으로 "
            "사용자의 질문에 친절하고 구체적으로 답변해주세요. "
            "추천할 때는 맛집의 이름, 특징, 평점을 자연스럽게 언급하세요. "
            "정보가 없다면 솔직하게 모른다고 답하고, 지어내지 마세요.\n\n"
            f"[참고 정보]\n{context_text}\n"
        )
        
        full_prompt = f"{system_instruction}\n\n사용자 질문: {user_message}"

        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(full_prompt)
            answer = response.text
            
            return JsonResponse({
                'answer': answer,
                'recommendations': [
                    {'name': r.name, 'rating': r.rating, 'address': r.address} 
                    for r in similar_restaurants
                ]
            })

        except Exception as e:
            return JsonResponse({'error': f'LLM 생성 오류: {str(e)}'}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        