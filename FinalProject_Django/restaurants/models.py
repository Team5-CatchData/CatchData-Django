from django.db import models
from pgvector.django import VectorField


class Restaurant(models.Model):
    # 기본 정보
    name = models.CharField(max_length=100)      # place_name
    address = models.CharField(max_length=255)   # road_address_name
    category = models.CharField(max_length=100)  # category_name
    phone = models.CharField(max_length=50, blank=True, default='')

    # 상세 정보 (메타데이터)
    rating = models.FloatField(default=0.0)      # rating
    review_count = models.IntegerField(default=0)  # review_count
    blog_count = models.IntegerField(default=0)  # blog_count

    place_url = models.URLField(blank=True)      # id를 이용해 생성 예정
    img_url = models.URLField(blank=True, max_length=500)  # img_url

    # 위치 정보
    x = models.FloatField(null=True, blank=True)  # x 좌표 (경도)
    y = models.FloatField(null=True, blank=True)  # y 좌표 (위도)
    location = models.CharField(max_length=50)   # address_name에서 구/동 추출

    # 추가 분석 데이터
    hourly_visit = models.TextField(blank=True, default='')

    # RAG 핵심: 검색용 텍스트와 벡터
    description = models.TextField()
    embedding = VectorField(dimensions=768)  # Gemini Embedding-004

    # 실시간/기타
    current_waiting_team = models.IntegerField(default=0)  # waiting
    average_waiting_time = models.IntegerField(default=20)

    def __str__(self):
        return f"{self.name} ({self.rating})"