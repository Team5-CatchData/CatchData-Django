from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Restaurant


def llm(request):
    """LLM 채팅 페이지"""
    return render(request, 'llm.html')


def restaurant_detail(request, restaurant_id):
    """레스토랑 상세 페이지"""
    restaurant = get_object_or_404(Restaurant, restaurant_ID=restaurant_id)
    context = {
        'restaurant': restaurant
    }
    return render(request, 'restaurant_detail.html', context)


@require_http_methods(["GET"])
def get_restaurant_name(request, restaurant_id):
    """레스토랑 이름 조회 API"""
    try:
        restaurant = Restaurant.objects.get(restaurant_ID=restaurant_id)
        return JsonResponse({'name': restaurant.name})
    except Restaurant.DoesNotExist:
        return JsonResponse({'name': f'레스토랑 {restaurant_id}'}, status=200)


@require_http_methods(["GET"])
def get_similar_restaurants(request, restaurant_id):
    """비슷한 식당 추천 API"""
    try:
        # 현재 레스토랑 정보 가져오기
        current_restaurant = Restaurant.objects.get(restaurant_ID=restaurant_id)

        # 클러스터가 없으면 빈 리스트 반환
        if current_restaurant.cluster is None:
            return JsonResponse({'similar_restaurants': []})

        # 같은 클러스터에 속하면서 현재 레스토랑이 아닌 식당들을 rec_balanced 기준으로 정렬
        similar_restaurants = Restaurant.objects.filter(
            cluster=current_restaurant.cluster,
            rec_balanced__isnull=False
        ).exclude(
            restaurant_ID=restaurant_id
        ).order_by('-rec_balanced')[:5]

        results = []
        for restaurant in similar_restaurants:
            results.append({
                'restaurant_ID': restaurant.restaurant_ID,
                'name': restaurant.name,
                'category': restaurant.category,
                'rating': float(restaurant.rating) if restaurant.rating else 0,
                'rec_balanced': float(restaurant.rec_balanced) if restaurant.rec_balanced else 0
            })

        return JsonResponse({'similar_restaurants': results})
    except Restaurant.DoesNotExist:
        return JsonResponse({'error': '레스토랑을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
