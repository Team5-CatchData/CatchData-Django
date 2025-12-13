import json
import os

import requests
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Restaurant


def llm(request):
    """LLM 채팅 페이지"""
    return render(request, 'llm.html')


@require_http_methods(["POST"])
def chat_api(request):
    """LLM API 엔드포인트"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')

        # 실제 LLM API 호출
        # .env 파일에서 API URL 가져오기
        llm_api_url = os.getenv('LLM_API_URL', 'http://your-llm-api-url.com/api/chat')

        # 외부 API에 요청 보내기
        try:
            response = requests.post(
                llm_api_url,
                json={'message': user_message},
                headers={'Content-Type': 'application/json'},
                timeout=30  # 30초 타임아웃
            )

            # API 응답이 성공적인 경우
            if response.status_code == 200:
                api_response = response.json()
                # API에서 받은 응답을 그대로 반환
                return JsonResponse(api_response)
            else:
                # API 오류 응답
                return JsonResponse(
                    {'error': f'LLM API 오류: {response.status_code}'},
                    status=response.status_code
                )

        except requests.exceptions.Timeout:
            return JsonResponse(
                {'error': 'API 요청 시간이 초과되었습니다.'},
                status=504
            )
        except requests.exceptions.ConnectionError:
            # 연결 실패시 테스트 응답 반환 (개발용)
            test_response = {
                "restaurantID": ["2154588", "213213"],
                "answer": "홍대음식점 빨간어묵을 추천해드려요! 그리고 수제 햄버거 집 버거걱도 추천드립니다!",
            }
            return JsonResponse(test_response)
        except requests.exceptions.RequestException as e:
            return JsonResponse(
                {'error': f'API 요청 실패: {str(e)}'},
                status=500
            )

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': '잘못된 요청 형식입니다.'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


def restaurant_detail(request, restaurant_id):
    """레스토랑 상세 페이지"""
    restaurant = get_object_or_404(Restaurant, restaurant_id=restaurant_id)
    context = {
        'restaurant': restaurant
    }
    return render(request, 'restaurant_detail.html', context)
