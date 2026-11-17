from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Rol


def es_administrador(usuario):
    return bool(
        usuario.is_authenticated
        and usuario.is_active
        and (
            usuario.is_superuser
            or (
                hasattr(usuario, "rol")
                and usuario.rol.nombre == Rol.ADMIN
            )
        )
    )


class EsUsuarioActivo(BasePermission):
    message = "Tu usuario no tiene permiso para acceder a este recurso."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario.is_authenticated
            and usuario.is_active
        )


class EsEquipoDelCentro(BasePermission):
    message = "Tu usuario no tiene un rol habilitado para operar en el centro."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(
            usuario.is_authenticated
            and usuario.is_active
            and (
                usuario.is_superuser
                or (
                    hasattr(usuario, "rol")
                    and usuario.rol.nombre in (Rol.ADMIN, Rol.COORDINACION)
                )
            )
        )


class SoloAdministrador(BasePermission):
    message = "Esta operación requiere el rol Administrador."

    def has_permission(self, request, view):
        return es_administrador(request.user)

    def has_object_permission(self, request, view, obj):
        # Un administrador de la API no puede modificar un superusuario de Django.
        return (
            request.method in SAFE_METHODS
            or request.user.is_superuser
            or not obj.is_superuser
        )


class PermisoCatalogo(EsUsuarioActivo):
    message = "Solo los usuarios con un rol habilitado pueden acceder a los catálogos."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        usuario = request.user

        if not hasattr(usuario, "rol"):
            return False

        if usuario.rol.nombre not in (
            Rol.ADMIN,
            Rol.COORDINACION,
            Rol.SOLICITANTE,
        ):
            return False

        return (
            request.method in SAFE_METHODS
            or es_administrador(usuario)
        )


class SoloAdministradorParaEscritura(EsEquipoDelCentro):

    message = "No tenés permisos para realizar esta operación."

    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and (
                request.method in SAFE_METHODS
                or es_administrador(request.user)
            )
        )


class PermisoActividad(EsUsuarioActivo):
    message = "No tenés permiso para realizar esta operación sobre la actividad."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        if request.method in SAFE_METHODS:
            return True

        if es_administrador(usuario):
            return True

        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        if es_administrador(usuario):
            return True

        if request.method in SAFE_METHODS:
            return True

        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and obj.responsable_id == usuario.pk
        )


class PermisoParticipante(EsUsuarioActivo):
    message = "No tenés permiso para realizar esta operación sobre el participante."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        # Todos los usuarios activos pueden consultar.
        if request.method in SAFE_METHODS:
            return True

        # ADMIN puede realizar cualquier operación.
        if es_administrador(usuario):
            return True

        # SOLICITANTE puede crear, modificar y eliminar.
        # La propiedad del participante se valida más abajo.
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        # ADMIN puede operar sobre cualquier participante.
        if es_administrador(usuario):
            return True

        # Todos los usuarios activos pueden consultar.
        if request.method in SAFE_METHODS:
            return True

        # SOLICITANTE solamente puede modificar o eliminar
        # participantes que haya creado.
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and obj.creado_por_id == usuario.pk
        )


class PermisoReserva(BasePermission):
    """
    ADMIN: puede gestionar todas las reservas.
    COORDINACION: puede consultar todas las reservas.
    SOLICITANTE: puede consultar sus propias reservas y crear nuevas.
    """

    def has_permission(self, request, view):
        usuario = request.user

        if not usuario.is_authenticated or not usuario.is_active:
            return False

        # Permitir que ADMIN y SOLICITANTE accedan a estas acciones.
        # La validación de que sea dueño de la reserva se hace en la vista.
        if view.action in (
            "solicitar_equipamiento",
            "eliminar_solicitud_equipamiento",
            "quitar_aula",
        ):
            return (
                es_administrador(usuario)
                or (
                    hasattr(usuario, "rol")
                    and usuario.rol.nombre == Rol.SOLICITANTE
                )
            )

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        if request.method == "POST":
            return (
                es_administrador(usuario)
                or (
                    hasattr(usuario, "rol")
                    and usuario.rol.nombre == Rol.SOLICITANTE
                )
            )

        return es_administrador(usuario)


class PermisoReservaParticipante(EsUsuarioActivo):
    message = "No tenés permiso para realizar esta operación sobre la asociación."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        if request.method in SAFE_METHODS:
            return True

        if es_administrador(usuario):
            return True

        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        if es_administrador(usuario):
            return True

        if request.method in SAFE_METHODS:
            return True

        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and obj.reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists()
        )


class PermisoSolicitudEquipo(EsUsuarioActivo):
    message = "No tenés permiso para realizar esta operación sobre la solicitud de equipamiento."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        # Todos los usuarios activos pueden consultar.
        if request.method in SAFE_METHODS:
            return True

        # ADMIN puede realizar cualquier operación.
        if es_administrador(usuario):
            return True

        # SOLICITANTE puede operar solicitudes de equipamiento.
        # La propiedad de la reserva se valida en el ViewSet.
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        if es_administrador(usuario):
            return True

        # Todos los usuarios activos pueden consultar.
        if request.method in SAFE_METHODS:
            return True

        # SOLICITANTE solo puede operar solicitudes
        # asociadas a sus propias reservas.
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and obj.reserva.usuarios_asociados.filter(
                usuario=usuario,
                solicitante=True,
            ).exists()
        )


class PermisoEstadoReserva(EsUsuarioActivo):
    message = "No tenés permisos para realizar esta operación sobre los estados de reserva."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        # El administrador tiene permisos completos de lectura y escritura
        if es_administrador(usuario):
            return True

        # Coordinación y Solicitante tienen exclusivamente permisos de lectura (SAFE_METHODS)
        if request.method in SAFE_METHODS:
            return True

        # Cualquier método de escritura/modificación se deniega para el resto de roles
        return False

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        # El administrador puede operar sobre cualquier elemento (lectura y escritura)
        if es_administrador(usuario):
            return True

        # Las operaciones de lectura están permitidas para usuarios activos
        if request.method in SAFE_METHODS:
            return True

        # Cualquier intento de modificación por parte de coordinación o solicitante queda bloqueado
        return False


class PermisoUsuarioReserva(EsUsuarioActivo):
    message = "No tenés permiso para realizar esta operación sobre la asociación de usuarios a la reserva."

    def has_permission(self, request, view):
        usuario = request.user

        if not super().has_permission(request, view):
            return False

        # Todos los usuarios activos pueden consultar (lectura)
        if request.method in SAFE_METHODS:
            return True

        # El administrador tiene permisos completos de lectura y escritura
        if es_administrador(usuario):
            return True

        # Coordinación solo tiene permisos de lectura (los métodos seguros ya retornaron True arriba)
        if hasattr(usuario, "rol") and usuario.rol.nombre == Rol.COORDINACION:
            return False

        # Solicitante puede intentar operaciones de escritura (POST, PUT, PATCH, DELETE)
        # La validación de si es el solicitante de la reserva se valida a nivel de objeto (y/o serializer/servicio).
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
        )

    def has_object_permission(self, request, view, obj):
        usuario = request.user

        # El administrador puede operar sobre cualquier elemento
        if es_administrador(usuario):
            return True

        # Las operaciones de lectura están permitidas para usuarios activos
        if request.method in SAFE_METHODS:
            return True

        # Coordinación no puede modificar nada
        if hasattr(usuario, "rol") and usuario.rol.nombre == Rol.COORDINACION:
            return False

        from reservas.services import _es_solicitante

        # El solicitante solo puede modificar o eliminar si es el solicitante (solicitante=True) de esa reserva
        return (
            hasattr(usuario, "rol")
            and usuario.rol.nombre == Rol.SOLICITANTE
            and _es_solicitante(obj.reserva, usuario)
        )
