from django.contrib import admin
from django.urls import path

from reservas.views import aulas_disponibles


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/aulas-disponibles/",
        aulas_disponibles,
        name="aulas-disponibles",
    ),
]
