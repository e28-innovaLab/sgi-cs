from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json

from django.utils import timezone

from espacios.models import Aula, Equipamiento
from reservas.models import Actividad
from .queries import ACTIVAS, cantidad_asignada, cantidad_comprometida, coincide, estado, minuto


def segmentos_excedidos(intervalos, limite):
    """Barrido temporal: fin antes de inicio, sin sumar usos consecutivos."""
    eventos = defaultdict(lambda: {'inicios': [], 'fines': []})
    for inicio, fin, reserva_id, cantidad in intervalos:
        if fin > inicio and cantidad > 0:
            eventos[inicio]['inicios'].append((reserva_id, cantidad))
            eventos[fin]['fines'].append(reserva_id)
    momentos = sorted(eventos)
    activos = {}
    for indice, momento in enumerate(momentos[:-1]):
        for pk in eventos[momento]['fines']:
            activos.pop(pk, None)
        for pk, cantidad in eventos[momento]['inicios']:
            activos[pk] = cantidad
        total = sum(activos.values())
        if total > limite:
            yield momento, momentos[indice + 1], sorted(activos), total


def alertas(reservas, filtros):
    seleccionadas = [r for r in reservas if coincide(r, filtros)]
    ids = {r.pk for r in seleccionadas}
    resultado = []

    def agregar(tipo, mensaje, *, nivel='ADVERTENCIA', reserva_ids=(), aula_id=None,
                equipamiento_id=None, fecha=None, inicio=None, fin=None, detalles=None):
        fila = {
            'tipo': tipo, 'nivel': nivel, 'mensaje': mensaje,
            'reserva_ids': list(reserva_ids), 'aula_id': aula_id,
            'equipamiento_id': equipamiento_id, 'fecha': fecha,
            'hora_inicio': str(timedelta(minutes=inicio)) if inicio is not None else None,
            'hora_fin': str(timedelta(minutes=fin)) if fin is not None else None,
            'detalles': detalles or {},
        }
        identidad = json.dumps(fila, sort_keys=True, default=str).encode()
        fila['id'] = hashlib.sha256(identidad).hexdigest()[:24]
        resultado.append(fila)

    aulas = Aula.objects.order_by('pk')
    equipos = Equipamiento.objects.order_by('pk')
    if 'aula' in filtros:
        aulas = aulas.filter(pk=filtros['aula'])
        pedidos = {s.equipamiento_id for r in seleccionadas for s in r.solicitudes_equipo.all()}
        from django.db.models import Q
        equipos = equipos.filter(Q(aula_id=filtros['aula']) | Q(pk__in=pedidos))
    if 'equipamiento' in filtros:
        equipos = equipos.filter(pk=filtros['equipamiento'])
        aulas = aulas.filter(equipamientos__pk=filtros['equipamiento'])
    for aula in aulas:
        if aula.estado != Aula.Estado.DISPONIBLE:
            agregar('AULA_NO_DISPONIBLE', 'El aula requiere atención por su estado operativo.',
                    aula_id=aula.pk, detalles={'estado': aula.estado})
    for equipo in equipos:
        if equipo.estado != Equipamiento.Estado.DISPONIBLE:
            agregar('EQUIPO_NO_DISPONIBLE', 'El equipo requiere atención por su estado operativo.',
                    equipamiento_id=equipo.pk, detalles={'estado': equipo.estado})

    ahora = timezone.localtime()
    for reserva in seleccionadas:
        actual = estado(reserva)
        if actual == 'SIN_ESTADO':
            agregar('RESERVA_SIN_ESTADO', 'La reserva no tiene estado definido.',
                    reserva_ids=[reserva.pk], fecha=reserva.fecha_reserva)
        if actual not in ACTIVAS:
            continue
        base = {'reserva_ids': [reserva.pk], 'fecha': reserva.fecha_reserva}
        asignadas = list(reserva.aulas.all())
        aulas_ids = {a.pk for a in asignadas}
        if not asignadas:
            agregar('RESERVA_SIN_AULA', 'La reserva no tiene espacio asignado.', **base)
        elif sum(a.capacidad for a in asignadas) < reserva.actividad.participantes_estimados:
            agregar('CAPACIDAD_INSUFICIENTE', 'La capacidad asignada es menor a la cantidad estimada.',
                    nivel='CRITICA', **base)
        for aula in asignadas:
            if aula.estado != Aula.Estado.DISPONIBLE:
                agregar('AULA_ASIGNADA_NO_DISPONIBLE', 'Una reserva activa tiene un aula no operativa.',
                        nivel='CRITICA', aula_id=aula.pk, **base)
        limite = reserva.horario_inicio if actual == 'Pendiente' else reserva.horario_fin
        if datetime.combine(reserva.fecha_reserva, limite) <= ahora.replace(tzinfo=None):
            agregar('RESERVA_VENCIDA', 'El estado requiere actualización por vencimiento del horario.', **base)
        solicitudes = list(reserva.solicitudes_equipo.all())
        if reserva.actividad.equipamiento_necesario.strip() and not solicitudes:
            agregar('REQUERIMIENTO_SIN_SOLICITUD',
                    'La actividad declara equipamiento necesario pero no tiene solicitudes registradas.', **base)
        for solicitud in solicitudes:
            equipo = solicitud.equipamiento
            asignada = cantidad_asignada(solicitud)
            if asignada < solicitud.cantidad_solicitada:
                agregar('EQUIPAMIENTO_PENDIENTE', 'La solicitud no está cubierta por completo.',
                        nivel='CRITICA' if asignada < solicitud.cantidad_critica else 'ADVERTENCIA',
                        equipamiento_id=equipo.pk, detalles={
                            'solicitada': solicitud.cantidad_solicitada, 'asignada': asignada,
                            'critica': solicitud.cantidad_critica,
                        }, **base)
            if equipo.estado != Equipamiento.Estado.DISPONIBLE:
                agregar('EQUIPO_ASIGNADO_NO_DISPONIBLE', 'Una reserva activa requiere un equipo no operativo.',
                        nivel='CRITICA', equipamiento_id=equipo.pk, **base)
            if not equipo.trasladable and equipo.aula_id not in aulas_ids:
                agregar('EQUIPO_FIJO_FUERA_DE_AULA', 'El equipo fijo no pertenece a las aulas asignadas.',
                        nivel='CRITICA', equipamiento_id=equipo.pk, **base)

    por_aula, por_equipo = defaultdict(list), defaultdict(list)
    stock = {}
    for reserva in reservas:
        if estado(reserva) not in ACTIVAS:
            continue
        inicio, fin = minuto(reserva.horario_inicio), minuto(reserva.horario_fin)
        for aula in reserva.aulas.all():
            por_aula[(aula.pk, reserva.fecha_reserva)].append((inicio, fin, reserva.pk, 1))
        for solicitud in reserva.solicitudes_equipo.all():
            pk = solicitud.equipamiento_id
            stock[pk] = solicitud.equipamiento.cantidad
            por_equipo[(pk, reserva.fecha_reserva)].append((
                inicio, fin, reserva.pk, cantidad_comprometida(solicitud),
            ))
    for (pk, fecha), intervalos in sorted(por_aula.items()):
        if 'aula' in filtros and pk != filtros['aula']:
            continue
        for inicio, fin, involucradas, total in segmentos_excedidos(intervalos, 1):
            if ids.intersection(involucradas):
                agregar('AULA_SUPERPUESTA', 'Hay reservas activas superpuestas en la misma aula.',
                        nivel='CRITICA', reserva_ids=involucradas, aula_id=pk, fecha=fecha,
                        inicio=inicio, fin=fin)
    for (pk, fecha), intervalos in sorted(por_equipo.items()):
        if 'equipamiento' in filtros and pk != filtros['equipamiento']:
            continue
        for inicio, fin, involucradas, total in segmentos_excedidos(intervalos, stock[pk]):
            if ids.intersection(involucradas):
                agregar('STOCK_SUPERADO', 'Las cantidades simultáneas superan el stock actual.',
                        nivel='CRITICA', reserva_ids=involucradas, equipamiento_id=pk,
                        fecha=fecha, inicio=inicio, fin=fin,
                        detalles={'comprometido': total, 'stock_actual': stock[pk]})

    actividades = Actividad.objects.filter(
        fecha_estimada__range=(filtros['desde'], filtros['hasta']),
    ).exclude(reservas__estado_reserva__estado__in=[*ACTIVAS, 'Finalizada']).order_by('pk')
    if 'tipo_actividad' in filtros:
        actividades = actividades.filter(tipo=filtros['tipo_actividad'])
    if not any(k in filtros for k in ('aula', 'equipamiento', 'reserva', 'estado')):
        for actividad in actividades:
            agregar('ACTIVIDAD_SIN_RESERVA', 'La actividad no tiene reserva vigente ni finalizada.',
                    fecha=actividad.fecha_estimada, detalles={'actividad_id': actividad.pk})
    if 'nivel' in filtros:
        resultado = [fila for fila in resultado if fila['nivel'] == filtros['nivel']]
    return sorted(resultado, key=lambda a: (a['nivel'] != 'CRITICA', str(a['fecha']), a['tipo'], a['id']))
