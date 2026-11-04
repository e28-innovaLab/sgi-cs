from django.contrib import admin
from django.urls import path
from django.urls import include
from rest_framework.routers import DefaultRouter

from reservas.views import aulas_disponibles
from espacios.views import AulaViewSet, CategoriaViewSet, EquipamientoViewSet
from usuarios.views import LoginView, LogoutView, PerfilView, RolViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('usuarios', UsuarioViewSet)
router.register('roles', RolViewSet)
router.register('aulas', AulaViewSet)
router.register('categorias', CategoriaViewSet)
router.register('equipamientos', EquipamientoViewSet)

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
