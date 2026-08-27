from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from resoluciones.views import generar_resolucion_view
from batch.views import descargar_lote, estado_lote, plantilla_csv, subir_lote


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/generate/", generar_resolucion_view, name="generar-resolucion"),
    path("batch/upload/", subir_lote, name="subir-lote"),
    path("batch/<uuid:batch_id>/estado/", estado_lote, name="estado-lote"),
    path("batch/<uuid:batch_id>/descargar/", descargar_lote, name="descargar-lote"),
    path("batch/template/", plantilla_csv, name="plantilla-csv"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
