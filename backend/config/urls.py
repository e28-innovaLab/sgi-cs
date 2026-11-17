from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from reservas.views import (
    ActividadViewSet,
    EstadoReservaViewSet,
    ParticipanteViewSet,
    ReservaParticipanteViewSet,
    ReservaViewSet,
    SolicitudEquipoViewSet,
    UsuarioPorReservaViewSet,
    aulas_disponibles,
)
from espacios.views import AulaViewSet, CategoriaViewSet, EquipamientoViewSet
from usuarios.views import LoginView, LogoutView, PerfilView, RolViewSet, UsuarioViewSet


router = DefaultRouter()
router.register('usuarios', UsuarioViewSet)
router.register('roles', RolViewSet)
router.register('aulas', AulaViewSet)
router.register('categorias', CategoriaViewSet)
router.register('equipamientos', EquipamientoViewSet)
router.register("reservas", ReservaViewSet, basename="reserva")
router.register("actividades", ActividadViewSet, basename="actividad")
router.register("participantes", ParticipanteViewSet, basename="participante")
router.register("reservas-participantes", ReservaParticipanteViewSet, basename="reserva-participante")
router.register("solicitudes-equipo", SolicitudEquipoViewSet, basename="solicitud-equipo")
router.register("estados-reservas", EstadoReservaViewSet, basename="estado-reserva")
router.register("usuarios-reservas", UsuarioPorReservaViewSet, basename="usuario-reserva")


urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', PerfilView.as_view(), name='perfil'),
    path('api/', include(router.urls)),
    path(
        "api/aulas-disponibles/",
        aulas_disponibles,
        name="aulas-disponibles",
    ),
]
