from django.shortcuts import get_object_or_404, render

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
