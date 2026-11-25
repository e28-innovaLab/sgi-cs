from django.db.models import Count, Prefetch, Q

from reservas.models import Reserva, SolicitudEquipo


ACTIVAS = ('Pendiente', 'Confirmada')
UTILIZACION = ('Confirmada', 'Finalizada')


def estado(reserva):
    return reserva.estado_reserva.estado if reserva.estado_reserva else 'SIN_ESTADO'


def cargar_reservas(filtros):
    return list(Reserva.objects.filter(fecha_reserva__range=(filtros['desde'], filtros['hasta']))
                .select_related('actividad', 'estado_reserva')
                .prefetch_related('aulas', Prefetch(
                    'solicitudes_equipo', queryset=SolicitudEquipo.objects.select_related('equipamiento'),
                )).annotate(
                    inscriptos=Count('reservas_participantes', distinct=True),
                    presentes=Count('reservas_participantes', filter=Q(reservas_participantes__presente=True), distinct=True),
                    ausentes=Count('reservas_participantes', filter=Q(reservas_participantes__presente=False), distinct=True),
                ).order_by('fecha_reserva', 'horario_inicio', 'pk'))


def coincide(reserva, filtros):
    return (
        ('reserva' not in filtros or reserva.pk == filtros['reserva'])
        and ('estado' not in filtros or estado(reserva) == filtros['estado'])
        and ('tipo_actividad' not in filtros or reserva.actividad.tipo == filtros['tipo_actividad'])
        and ('aula' not in filtros or any(a.pk == filtros['aula'] for a in reserva.aulas.all()))
        and ('equipamiento' not in filtros or any(
            s.equipamiento_id == filtros['equipamiento'] for s in reserva.solicitudes_equipo.all()
        ))
    )


def minuto(hora):
    return hora.hour * 60 + hora.minute + hora.second / 60 + hora.microsecond / 60000000


def duracion(reserva):
    return max(0, minuto(reserva.horario_fin) - minuto(reserva.horario_inicio))


def minutos_union(intervalos):
    total = 0
    fin_anterior = -1
    for inicio, fin in sorted(intervalos):
        if fin > inicio:
            total += max(0, fin - max(inicio, fin_anterior))
            fin_anterior = max(fin_anterior, fin)
    return total


def cantidad_asignada(solicitud):
    return solicitud.cantidad_reservada or 0


def cantidad_comprometida(solicitud):
    # Mantiene la semántica de la disponibilidad operativa existente.
    return (solicitud.cantidad_reservada if solicitud.cantidad_reservada is not None
            else solicitud.cantidad_solicitada)
