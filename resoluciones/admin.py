from django.contrib import admin

from .models import Resolucion, ResolucionMateria


class ResolucionMateriaInline(admin.TabularInline):
    model = ResolucionMateria
    extra = 1
    fields = ["materia", "carrera_origen", "equivalencia", "anio_cursado", "institucion", "situacion"]


@admin.register(Resolucion)
class ResolucionAdmin(admin.ModelAdmin):
    list_display = ["resolucion_nro", "alumno", "tecnicatura", "tipo", "estado", "fecha"]
    list_filter = ["estado", "tipo", "fecha"]
    search_fields = ["resolucion_nro", "alumno__nombre", "alumno__apellido", "alumno__dni"]
    autocomplete_fields = ["alumno", "tecnicatura"]
    inlines = [ResolucionMateriaInline]
