from django.urls import path

from . import views as main_views
from RAG import views as rag_views

app_name = 'main'
urlpatterns = [
    path('', main_views.llm, name='llm'),
    path('api/chat/', main_views.chat_api, name='chat_api'),
    path('restaurant/<str:restaurant_id>/', main_views.restaurant_detail, name='restaurant_detail'),
    path('api/ragchat/', rag_views.rag_chat_api, name='rag_api'),
]
