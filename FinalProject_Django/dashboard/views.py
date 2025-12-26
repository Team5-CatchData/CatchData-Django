import csv
import os
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from konlpy.tag import Okt
from collections import Counter

from main.models import Restaurant
from main.models import ChatHistory
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

        # Restaurant 모델에서 대기 인원이 있는 레스토랑
        restaurant_top = Restaurant.objects.filter(
            waiting__isnull=False
        ).order_by('-waiting')[:5]

        # MapSearchHistory 모델에서 대기 인원이 있는 레스토랑
        map_top = MapSearchHistory.objects.filter(
            waiting__isnull=False
        ).order_by('-waiting')[:5]

        # 두 모델의 데이터를 합쳐서 정렬
        all_restaurants = []

        for r in restaurant_top:
            all_restaurants.append({
                'name': r.name,
                'waiting': r.waiting,
                'category': r.category,
                'restaurant_ID': r.restaurant_ID
            })

        for m in map_top:
            all_restaurants.append({
                'name': m.name,
                'waiting': m.waiting,
                'category': m.category,
                'restaurant_ID': m.restaurant_ID
            })

        # 대기 인원 수로 정렬하고 상위 5개만 선택
        all_restaurants.sort(key=lambda x: x['waiting'], reverse=True)
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
        from collections import defaultdict

        from django.db.models import Sum

        category_waiting = defaultdict(int)

        # Restaurant 모델에서 카테고리별 대기 인원 합산
        restaurant_categories = Restaurant.objects.filter(
            waiting__isnull=False,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            total_waiting=Sum('waiting')
        )

        for item in restaurant_categories:
            category_waiting[item['category']] += item['total_waiting']

        # MapSearchHistory 모델에서 카테고리별 대기 인원 합산
        map_categories = MapSearchHistory.objects.filter(
            waiting__isnull=False,
            category__isnull=False
        ).exclude(category='').values('category').annotate(
            total_waiting=Sum('waiting')
        )

        for item in map_categories:
            category_waiting[item['category']] += item['total_waiting']

        # 딕셔너리를 리스트로 변환하고 정렬
        category_list = [
            {'category': category, 'total_waiting': total}
            for category, total in category_waiting.items()
        ]
        category_list.sort(key=lambda x: x['total_waiting'], reverse=True)

        # Top 5만 선택
        top_5_categories = category_list[:5]

        return JsonResponse({
            'top_categories': top_5_categories
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_top_by_recommendation(request):
    """추천도 기반 Top 5 레스토랑 조회 API"""
    try:
        rec_type = request.GET.get('type', 'quality')

        # 추천도 타입에 따라 정렬 필드 결정
        field_mapping = {
            'quality': 'rec_quality',
            'balanced': 'rec_balanced',
            'convenience': 'rec_convenience'
        }

        order_field = field_mapping.get(rec_type, 'rec_quality')

        # Restaurant 모델에서 추천도 기준으로 상위 5개 조회
        top_restaurants = Restaurant.objects.filter(
            **{f'{order_field}__isnull': False}
        ).order_by(f'-{order_field}')[:5]

        results = []
        for r in top_restaurants:
            rec_value = getattr(r, order_field, 0)
            results.append({
                'restaurant_ID': r.restaurant_ID,
                'name': r.name,
                'category': r.category,
                'rating': float(r.rating) if r.rating else 0,
                'rec_value': float(rec_value) if rec_value else 0
            })

        return JsonResponse({
            'top_restaurants': results,
            'rec_type': rec_type
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_filter_options(request):
    """필터 옵션 조회 API"""
    try:
        # Restaurant 모델과 MapSearchHistory 모델 모두에서 조회
        restaurant_regions = Restaurant.objects.values_list(
            'region', flat=True
        ).distinct()
        map_regions = MapSearchHistory.objects.values_list(
            'region', flat=True
        ).distinct()
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
        region_cities = {
            region: sorted(list(cities))
            for region, cities in region_cities.items()
        }

        restaurant_categories = Restaurant.objects.values_list(
            'category', flat=True
        ).distinct()
        map_categories = MapSearchHistory.objects.values_list(
            'category', flat=True
        ).distinct()
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
                    'waiting': r.waiting if r.waiting is not None else 0
                })

        # MapSearchHistory 모델 결과 변환
        map_results = list(map_queryset.values(
            'restaurant_ID', 'name', 'category', 'region', 'city', 'x', 'y', 'waiting'
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

@require_http_methods(["GET"])
def get_wordcloud_data(request):
    """
    채팅 기록을 분석하여 워드클라우드용 단어 빈도수 데이터를 반환하는 API
    """
    try:
        # 1. RDS에서 모든 사용자 질문(query) 가져오기
        # values_list를 사용하여 쿼리 최적화 (필요한 필드만 가져옴)
        queries = ChatHistory.objects.values_list('query', flat=True)
        
        if not queries:
            return JsonResponse({'words': []})

        # 2. 텍스트 합치기
        full_text = " ".join(queries)

        # 3. 자연어 처리 (형태소 분석)
        # Okt (Open Korean Text) 분석기 사용
        okt = Okt()
        nouns = okt.nouns(full_text)  # 명사만 추출

        # 4. 불용어 처리 (제외하고 싶은 단어들)
        # 맛집 추천 서비스 특성상 의미 없는 단어나 너무 뻔한 단어 제외
        stop_words = ['저', '요', '것', '집', '곳', '좀', '수', '등', '나', '추천', '맛집', '오늘', '내일']
        filtered_nouns = [word for word in nouns if word not in stop_words and len(word) > 1]

        # 5. 빈도수 계산
        count = Counter(filtered_nouns)
        
        # 상위 50개 단어만 추출
        top_words = count.most_common(50)

        # 6. 프론트엔드에서 쓰기 편한 리스트(딕셔너리) 형태로 변환
        # 예: [{'x': '파스타', 'value': 10}, {'x': '강남', 'value': 5}, ...]
        # AnyChart나 WordCloud 라이브러리들이 보통 {x: "단어", value: 빈도} 형태를 선호함
        word_data = [
            {'x': word, 'value': frequency} 
            for word, frequency in top_words
        ]

        return JsonResponse({
            'words': word_data,
            'total_count': len(filtered_nouns)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_local_wordcloud_data(request):
    """
    [로컬 테스트용] CSV 파일에서 데이터를 읽어 워드클라우드용 JSON을 반환하는 API
    """
    try:
        # 1. CSV 파일 경로 설정 (manage.py가 있는 폴더 기준)
        csv_path = os.path.join(settings.BASE_DIR, 'dummy_chat_data.csv')
        
        queries = []
        
        # 2. CSV 파일 읽기
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 'query' 컬럼이 있는지 확인하고 데이터 수집
                    if 'query' in row:
                        queries.append(row['query'])
        else:
            return JsonResponse({'error': f'파일을 찾을 수 없습니다: {csv_path}'}, status=404)

        if not queries:
            return JsonResponse({'words': []})

        # 3. 텍스트 합치기
        full_text = " ".join(queries)

        # 4. 자연어 처리 (형태소 분석 - 명사 추출)
        okt = Okt()
        nouns = okt.nouns(full_text)

        # 5. 불용어 처리
        stop_words = ['저', '요', '것', '집', '곳', '좀', '수', '등', '나', '추천', '맛집', '오늘', '내일', '근처', '어디', '알려']
        filtered_nouns = [word for word in nouns if word not in stop_words and len(word) > 1]

        # 6. 빈도수 계산 (Top 50)
        count = Counter(filtered_nouns)
        top_words = count.most_common(50)

        # 7. 데이터 포맷 변환 (AnyChart 호환)
        word_data = [
            {'x': word, 'value': frequency} 
            for word, frequency in top_words
        ]

        return JsonResponse({
            'words': word_data,
            'total_count': len(filtered_nouns),
            'source': 'local_csv' # 디버깅용 표시
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)