from django.contrib import admin
from .models import Aula, Categoria, Equipamiento


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("id_aula", "nombre", "capacidad", "sillas", "mesas", "color")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id_categoria", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Equipamiento)
class EquipamientoAdmin(admin.ModelAdmin):
    list_display = (
        "id_equipo",
        "nombre",
        "categoria",
        "aula",
        "cantidad",
        "estado",
        "trasladable",
    )
    list_filter = ("categoria", "estado", "trasladable")
    search_fields = ("nombre",)
    ordering = ("nombre",)
