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
