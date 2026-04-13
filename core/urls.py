from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('painel-atribuicao/', views.painel_atribuicao, name='painel_atribuicao'),
    path('painel-ranking/', views.painel_ranking, name='painel_ranking'),
    path('vendas/', views.vendas, name='vendas'),
    path('cockpit/', views.cockpit, name='cockpit'),
]
