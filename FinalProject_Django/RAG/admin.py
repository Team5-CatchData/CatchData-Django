from django.contrib import admin
from .models import EmbeddedData

@admin.register(EmbeddedData)
class EmbeddedDataAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'category',
        'address',
        'rating',
        'current_waiting_team',
    )
    
    search_fields = ('name', 'category', 'address')
    
    list_filter = ('category',)
    
    ordering = ('-rating',)