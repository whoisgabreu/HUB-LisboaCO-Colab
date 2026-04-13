from django.urls import path
from . import views

urlpatterns = [
    path('', views.operacao, name='operacao'),
    path('criativa/', views.criativa, name='criativa'),
    path('hub-cs-cx/', views.hub_cs_cx, name='hub_cs_cx'),
    
    # API
    path('api/tarefas/<int:pipefy_id>', views.api_get_tarefas, name='api_get_tarefas'),
    path('api/tarefas/toggle', views.api_toggle_tarefa, name='api_toggle_tarefa'),
    path('api/links/<int:pipefy_id>', views.api_get_links, name='api_get_links'),
]
