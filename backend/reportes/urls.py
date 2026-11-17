from django.urls import path

from .consulta_inteligente.api import ConsultaInteligenteView
from .importaciones.api import ImportacionView, PlantillaImportacionView

from .views import AlertasView, EquipamientoView, EspaciosView, HistorialView, ResumenView, UtilizacionHistoricaView


urlpatterns = [
    path('importaciones/aulas/', ImportacionView.as_view(tipo='aulas'), name='importar-aulas'),
    path('importaciones/equipamientos/', ImportacionView.as_view(tipo='equipamientos'), name='importar-equipamientos'),
    path('importaciones/plantillas/aulas/', PlantillaImportacionView.as_view(tipo='aulas'), name='plantilla-aulas'),
    path('importaciones/plantillas/equipamientos/', PlantillaImportacionView.as_view(tipo='equipamientos'), name='plantilla-equipamientos'),
    path('consulta-inteligente/', ConsultaInteligenteView.as_view(), name='consulta-inteligente'),
    path('indicadores/resumen/', ResumenView.as_view(), name='indicadores-resumen'),
    path('indicadores/espacios/', EspaciosView.as_view(), name='indicadores-espacios'),
    path('indicadores/equipamiento/', EquipamientoView.as_view(), name='indicadores-equipamiento'),
    path('alertas/', AlertasView.as_view(), name='alertas'),
    path('historial/reservas/', HistorialView.as_view(), name='historial-reservas'),
    path('historial/utilizacion/', UtilizacionHistoricaView.as_view(), name='historial-utilizacion'),
]
