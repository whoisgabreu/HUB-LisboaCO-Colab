from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),
    path('upload-profile-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    
    # Admin
    path('gerenciar-usuarios/', views.gerenciar_usuarios, name='gerenciar_usuarios'),
    path('api/admin/usuarios', views.api_get_usuarios, name='api_get_usuarios'),
    path('api/admin/save-usuario', views.api_save_usuario, name='api_save_usuario'),
    path('api/admin/reset-password', views.api_reset_password, name='api_reset_password'),
]
