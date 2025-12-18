from django.contrib import admin
from .models import Restaurant

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'rating', 'location')
    search_fields = ('name', 'description')
    readonly_fields = ('embedding_preview',)

    def embedding_preview(self, obj):
        if obj.embedding:
            return f"Vector (Size: {len(obj.embedding)}) - Example: {obj.embedding[:5]} ..."
        return "No embedding data"

    embedding_preview.short_description = "Embedding Vector"
    