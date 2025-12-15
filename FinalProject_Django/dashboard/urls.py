from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/filter-options/', views.get_filter_options, name='filter_options'),
    path('api/filter-restaurants/', views.filter_restaurants, name='filter_restaurants'),
]
