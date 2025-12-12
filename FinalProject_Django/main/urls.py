from django.urls import path
from . import views

app_name = 'main'
urlpatterns = [
    path('', views.llm, name='llm'),
    path('api/chat/', views.chat_api, name='chat_api'),
]