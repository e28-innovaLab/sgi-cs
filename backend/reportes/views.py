from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from . import alerts, historical, indicators
from .models import HistorialReserva
from .queries import cargar_reservas
from .serializers import ConsultaReporteSerializer, HistorialReservaSerializer


class ConsultaMixin:
    alertas_por_defecto = False

    def filtros(self):
        serializer = ConsultaReporteSerializer(
            data=self.request.query_params.dict(), context={'alertas': self.alertas_por_defecto},
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class ResumenView(ConsultaMixin, APIView):
    def get(self, request):
        filtros = self.filtros()
        return Response(indicators.resumen(cargar_reservas(filtros), filtros))


class IndicadorListadoView(ConsultaMixin, ListAPIView):
    def list(self, request, *args, **kwargs):
        filtros = self.filtros()
        resultado = self.calcular(cargar_reservas(filtros), filtros)
        pagina = self.paginate_queryset(resultado)
        return self.get_paginated_response(pagina)


class EspaciosView(IndicadorListadoView):
    calcular = staticmethod(indicators.espacios)


class EquipamientoView(IndicadorListadoView):
    calcular = staticmethod(indicators.equipamiento)


class AlertasView(IndicadorListadoView):
    alertas_por_defecto = True
    calcular = staticmethod(alerts.alertas)


class HistorialView(ConsultaMixin, ListAPIView):
    serializer_class = HistorialReservaSerializer

    def get_queryset(self):
        filtros = self.filtros()
        registros = HistorialReserva.objects.filter(fecha_reserva__range=(filtros['desde'], filtros['hasta']))
        if 'reserva' in filtros:
            registros = registros.filter(reserva_original_id=filtros['reserva'])
        if 'estado' in filtros:
            registros = registros.filter(datos__estado=None if filtros['estado'] == 'SIN_ESTADO' else filtros['estado'])
        if 'tipo_actividad' in filtros:
            registros = registros.filter(datos__actividad__tipo=filtros['tipo_actividad'])
        # JSON contains no es portable a SQLite; filtrar con los IDs del snapshot.
        if 'aula' in filtros or 'equipamiento' in filtros:
            ids = []
            for registro in registros:
                datos = registro.datos
                if 'aula' in filtros and not any(a['pk'] == filtros['aula'] for a in datos['aulas']):
                    continue
                if 'equipamiento' in filtros and not any(e['equipamiento_id'] == filtros['equipamiento'] for e in datos['equipos']):
                    continue
                ids.append(registro.pk)
            registros = registros.filter(pk__in=ids)
        return registros


class UtilizacionHistoricaView(ConsultaMixin, APIView):
    def get(self, request):
        filtros = self.filtros()
        return Response({'periodo': indicators.periodo(filtros), 'serie_diaria': historical.consolidado(filtros)})
