from django.contrib import admin
from django.contrib import messages

from .models import Alumno, CarreraOrigen, Materia, Tecnicatura


class CatalogoAdmin(admin.ModelAdmin):
    list_filter = ["activo"]
    actions = ["dar_de_baja"]

    @admin.action(description="Dar de baja los catálogos seleccionados")
    def dar_de_baja(self, request, queryset):
        actualizados = queryset.filter(activo=True).update(activo=False)
        self.message_user(
            request,
            f"Se dieron de baja {actualizados} registro(s).",
            messages.SUCCESS,
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Alumno)
class AlumnoAdmin(CatalogoAdmin):
    list_display = ["apellido", "nombre", "dni", "activo"]
    search_fields = ["nombre", "apellido", "dni"]


@admin.register(CarreraOrigen)
class CarreraOrigenAdmin(CatalogoAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]


@admin.register(Tecnicatura)
class TecnicaturaAdmin(CatalogoAdmin):
    list_display = ["nombre", "res_ministerial", "activo"]
    search_fields = ["nombre", "res_ministerial"]


@admin.register(Materia)
class MateriaAdmin(CatalogoAdmin):
    list_display = ["nombre", "activo"]
    search_fields = ["nombre"]
