from django.db import models
from django.utils import timezone


class ChatHistory(models.Model):
    """LLM 채팅 기록 모델"""
    query = models.TextField(verbose_name="사용자 질문")
    answer = models.TextField(verbose_name="LLM 응답")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="생성 시간")

    class Meta:
        verbose_name = "채팅 기록"
        verbose_name_plural = "채팅 기록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.query[:50]}"


class Restaurant(models.Model):
    """레스토랑 정보 모델"""
    restaurant_ID = models.IntegerField(
        unique=True, verbose_name="레스토랑 ID", primary_key=True
    )
    name = models.CharField(max_length=200, verbose_name="레스토랑 이름")
    phone = models.CharField(max_length=20, blank=True, verbose_name="전화번호")
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="평점",
    )
    category = models.CharField(max_length=20, blank=True, verbose_name="카테고리")
    address = models.CharField(max_length=200, blank=True, verbose_name="주소")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    x = models.FloatField(null=True, blank=True, verbose_name="경도")
    y = models.FloatField(null=True, blank=True, verbose_name="위도")
    region = models.CharField(max_length=20, blank=True, verbose_name="지역")
    city = models.CharField(max_length=15, blank=True, verbose_name="도시")
    waiting = models.IntegerField(null=True, blank=True, verbose_name="대기 인원")
    rec_quality = models.FloatField(
        null=True, blank=True, verbose_name="추천 품질 점수"
    )
    rec_balanced = models.FloatField(
        null=True, blank=True, verbose_name="추천 균형 점수"
    )
    rec_convenience = models.FloatField(
        null=True, blank=True, verbose_name="추천 편의 점수"
    )
    cluster = models.IntegerField(null=True, blank=True, verbose_name="클러스터")

    class Meta:
        verbose_name = "레스토랑"
        verbose_name_plural = "레스토랑"
        #ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.restaurant_ID})"
