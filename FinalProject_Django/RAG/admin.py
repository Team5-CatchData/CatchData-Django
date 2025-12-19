from django.contrib import admin

from .models import EmbeddedData


@admin.register(EmbeddedData)
class EmbeddedDataAdmin(admin.ModelAdmin):
    # 관리자 목록 페이지에서 보여질 필드들
    list_display = (
        'id',
        'name',
        'category',
        'address',
        'rating',
        'current_waiting_team',
    )

    # 검색창에서 검색할 수 있는 필드
    search_fields = ('name', 'category', 'address')

    # 우측에 필터링 옵션 추가
    list_filter = ('category',)

    # 기본 정렬 순서 (평점 높은 순)
    ordering = ('-rating',)