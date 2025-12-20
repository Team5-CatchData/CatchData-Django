from django.urls import path

from . import views as main_views
from RAG import views as rag_views

app_name = 'main'
urlpatterns = [
    path('', main_views.llm, name='llm'),
    path('restaurant/<str:restaurant_id>/', main_views.restaurant_detail, name='restaurant_detail'),
    path('api/ragchat/', rag_views.rag_chat_api, name='rag_api'),
    path('api/restaurant/<str:restaurant_id>/name/', main_views.get_restaurant_name, name='get_restaurant_name'),
]
