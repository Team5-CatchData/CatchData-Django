from django.db import models


class Restaurant(models.Model):
    """레스토랑 정보 모델"""
    restaurant_ID = models.IntegerField(unique=True, null=True, verbose_name="레스토랑 ID")
    name = models.CharField(max_length=200, verbose_name="레스토랑 이름")
    phone = models.CharField(max_length=20, blank=True, verbose_name="전화번호")
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name="평점")
    category = models.CharField(max_length=20, blank=True, verbose_name="카테고리")
    address = models.CharField(max_length=200, blank=True, verbose_name="주소")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="이미지 URL")
    x = models.FloatField(null=True, blank=True, verbose_name="경도")
    y = models.FloatField(null=True, blank=True, verbose_name="위도")
    region = models.CharField(max_length=20, blank=True, verbose_name="지역")
    city = models.CharField(max_length=15, blank=True, verbose_name="도시")
    waitting = models.IntegerField(null=True, blank=True, verbose_name="대기 인원")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일시")

    class Meta:
        verbose_name = "레스토랑"
        verbose_name_plural = "레스토랑"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.restaurant_ID})"
