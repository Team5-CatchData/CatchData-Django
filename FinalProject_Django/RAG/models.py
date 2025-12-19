from django.db import models
from pgvector.django import VectorField


class EmbeddedData(models.Model):
    # 기본 정보
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    phone = models.CharField(max_length=50, blank=True, default="")

    # 상세 정보
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    blog_count = models.IntegerField(default=0)
    place_url = models.URLField(blank=True)
    img_url = models.URLField(blank=True, max_length=500)

    # 위치 정보
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    location = models.CharField(max_length=50)
    hourly_visit = models.TextField(blank=True, default="")

    # RAG 핵심
    description = models.TextField()
    embedding = VectorField(dimensions=768)

    # 실시간/기타
    current_waiting_team = models.IntegerField(default=0)
    estimated_waiting_time = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.rating})"
