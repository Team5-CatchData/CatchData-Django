from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from main.models import Restaurant
from .models import MapSearchHistory


def dashboard(request):
    """대시보드 페이지"""
    context = {
        'kakao_map_api_key': settings.KAKAO_MAP_API_KEY
    }
    return render(request, 'dashboard.html', context)


@require_http_methods(["GET"])
def get_top_restaurants(request):
    """대기 인원 수 기반 Top 5 레스토랑 조회 API"""
    try:
        # Restaurant와 MapSearchHistory 모두에서 조회
        from django.db.models import Q

        # Restaurant 모델에서 대기 인원이 있는 레스토랑
        restaurant_top = Restaurant.objects.filter(
            waitting__isnull=False
        ).order_by('-waitting')[:5]

        # MapSearchHistory 모델에서 대기 인원이 있는 레스토랑
        map_top = MapSearchHistory.objects.filter(
            waitting__isnull=False
        ).order_by('-waitting')[:5]

        # 두 모델의 데이터를 합쳐서 정렬
        all_restaurants = []

        for r in restaurant_top:
            all_restaurants.append({
                'name': r.name,
                'waitting': r.waitting,
                'category': r.category,
                'restaurant_ID': r.restaurant_ID
            })

        for m in map_top:
            all_restaurants.append({
                'name': m.name,
                'waitting': m.waitting,
                'category': m.category,
                'restaurant_ID': m.restaurant_ID
            })

        # 대기 인원 수로 정렬하고 상위 5개만 선택
        all_restaurants.sort(key=lambda x: x['waitting'], reverse=True)
        top_5 = all_restaurants[:5]

        return JsonResponse({
            'top_restaurants': top_5
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_top_categories(request):
    """카테고리별 대기 인원 합산 Top 5 조회 API"""
    try:
        from django.db.models import Sum
        from collections import defaultdict

        category_waitting = defaultdict(int)

        # Restaurant 모델에서 카테고리별 대기 인원 합산
        restaurant_categories = Restaurant.objects.filter(
            waitting__isnull=False,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            total_waitting=Sum('waitting')
        )

        for item in restaurant_categories:
            category_waitting[item['category']] += item['total_waitting']

        # MapSearchHistory 모델에서 카테고리별 대기 인원 합산
        map_categories = MapSearchHistory.objects.filter(
            waitting__isnull=False,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            total_waitting=Sum('waitting')
        )

        for item in map_categories:
            category_waitting[item['category']] += item['total_waitting']

        # 딕셔너리를 리스트로 변환하고 정렬
        category_list = [
            {'category': category, 'total_waitting': total}
            for category, total in category_waitting.items()
        ]
        category_list.sort(key=lambda x: x['total_waitting'], reverse=True)

        # Top 5만 선택
        top_5_categories = category_list[:5]

        return JsonResponse({
            'top_categories': top_5_categories
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_filter_options(request):
    """필터 옵션 조회 API"""
    try:
        # Restaurant 모델과 MapSearchHistory 모델 모두에서 조회
        restaurant_regions = Restaurant.objects.values_list('region', flat=True).distinct()
        map_regions = MapSearchHistory.objects.values_list('region', flat=True).distinct()
        all_regions = sorted(set(list(restaurant_regions) + list(map_regions)))
        all_regions = [r for r in all_regions if r]

        # 지역별 도시 매핑 생성
        region_cities = {}

        # Restaurant 모델에서 지역-도시 매핑
        for r in Restaurant.objects.values('region', 'city').distinct():
            if r['region'] and r['city']:
                if r['region'] not in region_cities:
                    region_cities[r['region']] = set()
                region_cities[r['region']].add(r['city'])

        # MapSearchHistory 모델에서 지역-도시 매핑
        for m in MapSearchHistory.objects.values('region', 'city').distinct():
            if m['region'] and m['city']:
                if m['region'] not in region_cities:
                    region_cities[m['region']] = set()
                region_cities[m['region']].add(m['city'])

        # set을 sorted list로 변환
        region_cities = {region: sorted(list(cities)) for region, cities in region_cities.items()}

        restaurant_categories = Restaurant.objects.values_list('category', flat=True).distinct()
        map_categories = MapSearchHistory.objects.values_list('category', flat=True).distinct()
        all_categories = sorted(set(list(restaurant_categories) + list(map_categories)))
        all_categories = [cat for cat in all_categories if cat]

        return JsonResponse({
            'regions': all_regions,
            'region_cities': region_cities,
            'categories': all_categories
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def filter_restaurants(request):
    """레스토랑 필터링 API"""
    import json
    try:
        data = json.loads(request.body)
        region = data.get('region')
        city = data.get('city')
        category = data.get('category')

        # Restaurant 모델에서 필터링
        restaurant_queryset = Restaurant.objects.all()
        if region:
            restaurant_queryset = restaurant_queryset.filter(region=region)
        if city:
            restaurant_queryset = restaurant_queryset.filter(city=city)
        if category:
            restaurant_queryset = restaurant_queryset.filter(category=category)

        # MapSearchHistory 모델에서 필터링
        map_queryset = MapSearchHistory.objects.all()
        if region:
            map_queryset = map_queryset.filter(region=region)
        if city:
            map_queryset = map_queryset.filter(city=city)
        if category:
            map_queryset = map_queryset.filter(category=category)

        # Restaurant 모델 결과 변환
        restaurant_results = []
        for r in restaurant_queryset:
            if r.x and r.y:  # 좌표가 있는 경우만 포함
                restaurant_results.append({
                    'restaurant_ID': r.restaurant_ID,
                    'name': r.name,
                    'category': r.category,
                    'region': r.region,
                    'city': r.city,
                    'x': r.x,
                    'y': r.y,
                    'waitting': r.waitting if r.waitting is not None else 0
                })

        # MapSearchHistory 모델 결과 변환
        map_results = list(map_queryset.values(
            'restaurant_ID', 'name', 'category', 'region', 'city', 'x', 'y', 'waitting'
        ))

        # 두 결과 합치기
        all_restaurants = restaurant_results + map_results

        return JsonResponse({
            'restaurants': all_restaurants,
            'count': len(all_restaurants)
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
