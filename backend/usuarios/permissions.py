from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Rol


def es_administrador(usuario):
    return bool(
        usuario.is_authenticated
        and usuario.is_active
        and (usuario.is_superuser or usuario.rol.nombre == Rol.ADMIN)
    )


class EsEquipoDelCentro(BasePermission):
    message = 'Tu usuario no tiene un rol habilitado para operar en el centro.'

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario.is_authenticated
            and usuario.is_active
            and (usuario.is_superuser or usuario.rol.nombre in (Rol.ADMIN, Rol.COORDINACION))
        )


class SoloAdministrador(BasePermission):
    message = 'Esta operación requiere el rol Administrador.'

    def has_permission(self, request, view):
        return es_administrador(request.user)

    def has_object_permission(self, request, view, obj):
        # Un administrador de la API no puede modificar un superusuario de Django.
        return request.method in SAFE_METHODS or request.user.is_superuser or not obj.is_superuser


class PermisoCatalogo(EsEquipoDelCentro):
    message = 'Solo Administración puede configurar espacios y equipamiento.'

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.method in SAFE_METHODS
            or es_administrador(request.user)
            or getattr(view, 'action', None) == 'actualizar_estado'
        )
