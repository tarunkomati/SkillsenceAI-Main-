from django.urls import path
from . import views

urlpatterns = [
    path('landing/', views.landing_content_view, name='landing-content'),
]
