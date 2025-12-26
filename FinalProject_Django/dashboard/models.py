# Create your models here.
from django.db import models


class MapSearchHistory(models.Model):
    """지도 검색 기록 모델"""
    restaurant_ID = models.IntegerField() # 주로 조회하는 값이니 char보다는 int로 수정
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20)
    region = models.CharField(max_length=20)
    city = models.CharField(max_length=15)
    x = models.FloatField()
    y = models.FloatField()
    waiting = models.IntegerField()

    def __str__(self):
            return f"{self.name} ({self.region})"
