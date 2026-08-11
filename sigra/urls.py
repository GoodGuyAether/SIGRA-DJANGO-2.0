from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from resoluciones.views import generar_resolucion_view


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/generate/", generar_resolucion_view, name="generar-resolucion"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
