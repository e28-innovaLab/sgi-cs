from collections import Counter, defaultdict
from datetime import time

from django.db.models import OuterRef, Subquery

from .models import HistorialReserva
from .queries import minuto


def consolidado(filtros):
    ultimos = HistorialReserva.objects.filter(reserva_original_id=OuterRef('reserva_original_id')).order_by('-pk')
    registros = HistorialReserva.objects.filter(
        pk=Subquery(ultimos.values('pk')[:1]),
        fecha_reserva__range=(filtros['desde'], filtros['hasta']),
    ).order_by('fecha_reserva', 'reserva_original_id')
    por_fecha = defaultdict(lambda: {
        'reservas': 0, 'eliminadas': 0, 'minutos_aula_finalizados': 0,
        'unidades_minuto_equipo_finalizados': 0, 'presentes': 0, 'estados': Counter(),
    })
    for registro in registros:
        datos = registro.datos
        if 'reserva' in filtros and registro.reserva_original_id != filtros['reserva']:
            continue
        if 'estado' in filtros and (datos['estado'] or 'SIN_ESTADO') != filtros['estado']:
            continue
        if 'tipo_actividad' in filtros and datos['actividad']['tipo'] != filtros['tipo_actividad']:
            continue
        aulas = datos['aulas']
        equipos = datos['equipos']
        if 'aula' in filtros:
            aulas = [a for a in aulas if a['pk'] == filtros['aula']]
            if not aulas:
                continue
        if 'equipamiento' in filtros:
            equipos = [e for e in equipos if e['equipamiento_id'] == filtros['equipamiento']]
            if not equipos:
                continue
        fila = por_fecha[registro.fecha_reserva]
        fila['reservas'] += 1
        fila['eliminadas'] += bool(datos.get('eliminada'))
        fila['estados'][datos['estado'] or 'SIN_ESTADO'] += 1
        if datos['estado'] == 'Finalizada':
            minutos = max(0, minuto(time.fromisoformat(datos['hora_fin'])) - minuto(time.fromisoformat(datos['hora_inicio'])))
            fila['minutos_aula_finalizados'] += minutos * len(aulas)
            fila['unidades_minuto_equipo_finalizados'] += minutos * sum(e['cantidad_reservada'] or 0 for e in equipos)
            fila['presentes'] += datos['asistencia']['presentes']
    return [{'fecha': fecha, **fila} for fecha, fila in sorted(por_fecha.items())]
