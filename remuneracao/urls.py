from django.urls import path
from . import views

urlpatterns = [
    path('hub-remuneracao', views.hub_remuneracao, name='hub_remuneracao'),
    path('api/processar', views.api_processar_remuneracao, name='api_processar_remuneracao'),
]
