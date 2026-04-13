from django.urls import path
from . import views

urlpatterns = [
    path('hub-projetos', views.hub_projetos, name='hub_projetos'),
]
