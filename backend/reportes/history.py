import hashlib
import json

from django.db import transaction
from django.db.models import Count, Q

from reservas.models import Reserva
from .models import HistorialReserva


def snapshot(reserva):
    asistencia = reserva.reservas_participantes.aggregate(
        inscriptos=Count('pk'), presentes=Count('pk', filter=Q(presente=True)),
        ausentes=Count('pk', filter=Q(presente=False)),
        sin_registrar=Count('pk', filter=Q(presente__isnull=True)),
    )
    return {
        'reserva_id': reserva.pk,
        'fecha': reserva.fecha_reserva.isoformat(),
        'hora_inicio': reserva.horario_inicio.isoformat(),
        'hora_fin': reserva.horario_fin.isoformat(),
        'estado': reserva.estado_reserva.estado if reserva.estado_reserva else None,
        'actividad': {
            'id': reserva.actividad_id, 'nombre': reserva.actividad.nombre,
            'tipo': reserva.actividad.tipo,
            'participantes_estimados': reserva.actividad.participantes_estimados,
        },
        'aulas': list(reserva.aulas.order_by('pk').values('pk', 'nombre', 'capacidad')),
        'equipos': list(reserva.solicitudes_equipo.order_by('equipamiento_id').values(
            'equipamiento_id', 'equipamiento__nombre', 'equipamiento__cantidad',
            'cantidad_solicitada', 'cantidad_reservada', 'cantidad_critica',
        )),
        'asistencia': asistencia,
    }


def registrar_reserva(reserva_id, evento='CAMBIO', using='default'):
    """Serializa la captura por reserva y no duplica snapshots consecutivos iguales."""
    with transaction.atomic(using=using):
        reserva = (Reserva.objects.using(using).select_for_update(of=('self',))
                   .select_related('actividad', 'estado_reserva').filter(pk=reserva_id).first())
        if reserva is None:
            return False
        datos = snapshot(reserva)
        if evento == 'ELIMINADA':
            datos['eliminada'] = True
        huella = hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()
        registros = HistorialReserva.objects.using(using).filter(reserva_original_id=reserva_id)
        ultimo = registros.order_by('-pk').first()
        if ultimo and ultimo.huella == huella:
            return False
        HistorialReserva.objects.using(using).create(
            reserva_original_id=reserva_id, fecha_reserva=reserva.fecha_reserva,
            evento=evento, datos=datos, huella=huella,
        )
        return True
