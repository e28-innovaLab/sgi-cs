from django.urls import path

from .views import AlertasView, EquipamientoView, EspaciosView, HistorialView, ResumenView, UtilizacionHistoricaView


urlpatterns = [
    path('indicadores/resumen/', ResumenView.as_view(), name='indicadores-resumen'),
    path('indicadores/espacios/', EspaciosView.as_view(), name='indicadores-espacios'),
    path('indicadores/equipamiento/', EquipamientoView.as_view(), name='indicadores-equipamiento'),
    path('alertas/', AlertasView.as_view(), name='alertas'),
    path('historial/reservas/', HistorialView.as_view(), name='historial-reservas'),
    path('historial/utilizacion/', UtilizacionHistoricaView.as_view(), name='historial-utilizacion'),
]
