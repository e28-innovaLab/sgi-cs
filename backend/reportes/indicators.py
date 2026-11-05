from collections import Counter, defaultdict

from espacios.models import Aula, Equipamiento
from .queries import UTILIZACION, cantidad_asignada, coincide, duracion, estado, minuto, minutos_union


def periodo(filtros):
    return {'desde': filtros['desde'], 'hasta': filtros['hasta']}


def resumen(reservas, filtros):
    seleccionadas = [r for r in reservas if coincide(r, filtros)]
    estados = Counter(estado(r) for r in seleccionadas)
    utilizadas = [r for r in seleccionadas if estado(r) in UTILIZACION]
    por_dia = defaultdict(lambda: {'reservas': 0, 'minutos_reservados': 0})
    for reserva in seleccionadas:
        fila = por_dia[reserva.fecha_reserva]
        fila['reservas'] += 1
        if estado(reserva) in UTILIZACION:
            fila['minutos_reservados'] += duracion(reserva)
    asistencia = {
        'inscriptos': sum(r.inscriptos for r in utilizadas),
        'presentes': sum(r.presentes for r in utilizadas),
        'ausentes': sum(r.ausentes for r in utilizadas),
    }
    asistencia['sin_registrar'] = asistencia['inscriptos'] - asistencia['presentes'] - asistencia['ausentes']
    return {
        'periodo': periodo(filtros), 'reservas_total': len(seleccionadas),
        'reservas_por_estado': dict(sorted(estados.items())),
        'reservas_activas': estados['Pendiente'] + estados['Confirmada'],
        'actividades_con_reserva': len({r.actividad_id for r in seleccionadas}),
        'minutos_reservados': round(sum(duracion(r) for r in utilizadas), 2),
        'asistencia': asistencia,
        'serie_diaria': [{'fecha': fecha, **fila} for fecha, fila in sorted(por_dia.items())],
    }


def espacios(reservas, filtros):
    aulas = Aula.objects.order_by('pk')
    if 'aula' in filtros:
        aulas = aulas.filter(pk=filtros['aula'])
    por_aula = defaultdict(list)
    for reserva in reservas:
        if coincide(reserva, filtros) and estado(reserva) in UTILIZACION:
            for aula in reserva.aulas.all():
                por_aula[aula.pk].append(reserva)
    apertura, cierre = minuto(filtros['hora_apertura']), minuto(filtros['hora_cierre'])
    referencia = (cierre - apertura) * ((filtros['hasta'] - filtros['desde']).days + 1)
    resultado = []
    for aula in aulas:
        por_fecha = defaultdict(list)
        asignadas = por_aula[aula.pk]
        for reserva in asignadas:
            por_fecha[reserva.fecha_reserva].append((
                max(apertura, minuto(reserva.horario_inicio)), min(cierre, minuto(reserva.horario_fin)),
            ))
        ocupados = sum(minutos_union(intervalos) for intervalos in por_fecha.values())
        resultado.append({
            'aula_id': aula.pk, 'nombre': aula.nombre, 'estado_actual': aula.estado,
            'reservas': len(asignadas),
            'minutos_ocupados': round(ocupados, 2), 'minutos_referencia': round(referencia, 2),
            'ocupacion_porcentaje': round(100 * ocupados / referencia, 2),
        })
    return sorted(resultado, key=lambda fila: (-fila['minutos_ocupados'], fila['aula_id']))


def equipamiento(reservas, filtros):
    equipos = Equipamiento.objects.order_by('pk')
    if 'equipamiento' in filtros:
        equipos = equipos.filter(pk=filtros['equipamiento'])
    if 'aula' in filtros:
        # Incluye los móviles pedidos para esa aula, aunque tengan otra ubicación habitual.
        pedidos = {s.equipamiento_id for r in reservas if coincide(r, filtros)
                   for s in r.solicitudes_equipo.all()}
        from django.db.models import Q
        equipos = equipos.filter(Q(aula_id=filtros['aula']) | Q(pk__in=pedidos))
    totales = defaultdict(lambda: {'reservas': 0, 'unidades_solicitadas': 0, 'unidades_minuto': 0})
    for reserva in reservas:
        if not coincide(reserva, filtros) or estado(reserva) not in (*UTILIZACION, 'Pendiente'):
            continue
        for solicitud in reserva.solicitudes_equipo.all():
            fila = totales[solicitud.equipamiento_id]
            fila['reservas'] += 1
            fila['unidades_solicitadas'] += solicitud.cantidad_solicitada
            if estado(reserva) in UTILIZACION:
                fila['unidades_minuto'] += cantidad_asignada(solicitud) * duracion(reserva)
    resultado = []
    for equipo in equipos:
        fila = dict(totales[equipo.pk])
        fila['unidades_minuto'] = round(fila['unidades_minuto'], 2)
        resultado.append({
            'equipamiento_id': equipo.pk, 'nombre': equipo.nombre,
            'cantidad_actual': equipo.cantidad, 'estado_actual': equipo.estado,
            'trasladable': equipo.trasladable, **fila,
        })
    return sorted(resultado, key=lambda fila: (-fila['unidades_minuto'], fila['equipamiento_id']))
