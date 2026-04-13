from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # path('admin/', admin.site.urls), # Opcional, o sistema tem admin próprio
    path('', include('core.urls')),
    path('auth/', include('users.urls')),
    path('projetos/', include('projetos.urls')),
    path('operacao/', include('operacao.urls')),
    path('remuneracao/', include('remuneracao.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
