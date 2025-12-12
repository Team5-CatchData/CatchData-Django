from django.shortcuts import render


def dashboard(request):
    """대시보드 페이지"""
    return render(request, 'dashboard.html')
