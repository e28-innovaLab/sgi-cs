from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id_rol", "nombre")
    search_fields = ("nombre",)
    ordering = ("id_rol",)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "rol",
        "is_active",
    )
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "numero_documento",
    )
