from django.urls import path

from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/top-restaurants/', views.get_top_restaurants, name='get_top_restaurants'),
    path('api/top-categories/', views.get_top_categories, name='get_top_categories'),
    path(
        'api/top-by-recommendation/',
        views.get_top_by_recommendation,
        name='get_top_by_recommendation',
    ),
    path('api/filter-options/', views.get_filter_options, name='get_filter_options'),
    path(
        'api/filter-restaurants/', views.filter_restaurants, name='filter_restaurants'
    ),
]
