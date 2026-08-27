from django.contrib import admin

from .models import LoteCarga


@admin.register(LoteCarga)
class LoteCargaAdmin(admin.ModelAdmin):
    list_display = ["batch_id", "archivo_original", "estado", "total_filas", "total_resoluciones", "creado_en"]
    list_filter = ["estado"]
    search_fields = ["batch_id", "archivo_original"]
    readonly_fields = ["batch_id", "archivo_original", "total_filas", "total_resoluciones", "errores", "estado", "creado_en"]
