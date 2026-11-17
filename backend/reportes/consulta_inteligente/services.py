from django.utils import timezone

from reservas.services import obtener_aulas_disponibles
from reportes import alerts, indicators
from reportes.queries import cargar_reservas
from reportes.serializers import ConsultaReporteSerializer

from .parser import PreguntaNoReconocida


def _filtros(plan):
    parametros = {k: v for k, v in plan['parametros'].items() if k not in ('orden', 'metrica', 'tema')}
    serializer = ConsultaReporteSerializer(
        data=parametros, context={'alertas': plan['intencion'] == 'alertas_operativas'},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _disponibilidad(parametros, limite):
    if parametros['fecha'] < timezone.localdate():
        raise PreguntaNoReconocida('Para consultar disponibilidad indicá hoy o una fecha futura.')
    fecha = parametros['fecha']
    aulas = obtener_aulas_disponibles(fecha, parametros['hora_inicio'], parametros['hora_fin'])
    if 'capacidad_min' in parametros:
        aulas = aulas.filter(capacidad__gte=parametros['capacidad_min'])
    if 'tipo_aula' in parametros:
        aulas = aulas.filter(tipo=parametros['tipo_aula'])
    # Respeta los días habilitados por las validaciones actuales de reservas.
    if fecha.weekday() >= 5:
        aulas = aulas.none()
    aulas = aulas.order_by('nombre', 'pk')
    total = aulas.count()
    filas = [{'aula_id': a.pk, 'nombre': a.nombre, 'capacidad': a.capacidad, 'tipo': a.tipo}
             for a in aulas[:limite]]
    datos = {**parametros, 'total': total, 'resultados': filas}
    franja = f"{fecha.isoformat()}, de {parametros['hora_inicio']:%H:%M} a {parametros['hora_fin']:%H:%M}"
    if fecha.weekday() >= 5:
        respuesta = 'No se programan reservas en sábados ni domingos según las reglas actuales del centro.'
    elif total:
        respuesta = f'Hay {total} espacios disponibles para {franja}. Esta consulta no realiza una reserva.'
    else:
        respuesta = f'No hay espacios disponibles que cumplan la consulta para {franja}.'
    return respuesta, datos, ['espacios', 'reservas', '/api/aulas-disponibles/']


def resolver_consulta(plan, limite=5):
    """Despacha intenciones previstas a consultas ORM; no genera SQL ni escribe datos."""
    intencion, parametros = plan['intencion'], plan['parametros']
    if intencion == 'disponibilidad_aulas':
        return _disponibilidad(parametros, limite)

    filtros = _filtros(plan)
    reservas = cargar_reservas(filtros)
    periodo = indicators.periodo(filtros)
    texto_periodo = f"del {filtros['desde'].isoformat()} al {filtros['hasta'].isoformat()}"

    if intencion == 'resumen_reservas':
        datos = indicators.resumen(reservas, filtros)
        total = datos['reservas_total']
        if total:
            desglose = ', '.join(f'{estado}: {cantidad}' for estado, cantidad in datos['reservas_por_estado'].items())
            respuesta = f'Hay {total} reservas registradas {texto_periodo}. {desglose}.'
        else:
            respuesta = f'No hay reservas registradas que coincidan con la consulta {texto_periodo}.'
        return respuesta, datos, ['reservas', '/api/indicadores/resumen/']

    if intencion in ('utilizacion_espacios', 'utilizacion_equipos'):
        ascendente = parametros.get('orden') == 'asc'
        comparacion = 'menor' if ascendente else 'mayor'
        if intencion == 'utilizacion_espacios':
            filas = indicators.espacios(reservas, filtros)
            campo, campo_id = 'minutos_ocupados', 'aula_id'
            fuente = '/api/indicadores/espacios/'
        else:
            filas = indicators.equipamiento(reservas, filtros)
            campo = 'unidades_solicitadas' if parametros.get('metrica') == 'demanda' else 'unidades_minuto'
            campo_id, fuente = 'equipamiento_id', '/api/indicadores/equipamiento/'
        filas.sort(key=lambda fila: (fila[campo] if ascendente else -fila[campo], fila[campo_id]))
        datos = {'periodo': periodo, 'total': len(filas), 'resultados': filas[:limite]}
        if not filas:
            respuesta = f'No hay recursos registrados para esta consulta {texto_periodo}.'
        elif not any(fila[campo] for fila in filas):
            respuesta = f'No se registró {"demanda" if campo == "unidades_solicitadas" else "utilización"} de estos recursos {texto_periodo}.'
        else:
            primera = filas[0]
            if intencion == 'utilizacion_espacios':
                respuesta = (f"El espacio con {comparacion} ocupación {texto_periodo} es {primera['nombre']}: "
                             f"{primera['ocupacion_porcentaje']}% de la ventana de referencia "
                             '(08:00–20:00). Es tiempo reservado, no una medición de presencia real.')
            elif campo == 'unidades_solicitadas':
                respuesta = (f"El equipo con {comparacion} demanda {texto_periodo} es {primera['nombre']}: "
                             f"{primera[campo]} unidades solicitadas en el período.")
            else:
                respuesta = (f"El equipo con {comparacion} utilización registrada {texto_periodo} es "
                             f"{primera['nombre']}: {primera[campo]} unidades-minuto asignadas.")
        return respuesta, datos, ['reservas', 'espacios', fuente]

    if intencion == 'alertas_operativas':
        filas = alerts.alertas(reservas, filtros)
        tema = parametros.get('tema', 'todas')
        if tema == 'equipamiento':
            filas = [f for f in filas if f['equipamiento_id'] is not None
                     or f['tipo'] == 'REQUERIMIENTO_SIN_SOLICITUD']
        elif tema == 'espacios':
            filas = [f for f in filas if f['aula_id'] is not None or f['tipo'] in (
                'RESERVA_SIN_AULA', 'CAPACIDAD_INSUFICIENTE',
            )]
        # Agrega únicamente la identificación de la actividad; no datos de personas.
        actividades = {r.pk: {'id': r.actividad_id, 'nombre': r.actividad.nombre} for r in reservas}
        filas = [{**f, 'actividades': [actividades[pk] for pk in f['reserva_ids'] if pk in actividades]}
                 for f in filas]
        datos = {'periodo': periodo, 'total': len(filas), 'resultados': filas[:limite]}
        respuesta = (f'Hay {len(filas)} alertas para esta consulta {texto_periodo}.' if filas else
                     f'No se detectaron alertas para esta consulta {texto_periodo}.')
        nombres = list(dict.fromkeys(a['nombre'] for f in filas for a in f['actividades']))
        if nombres:
            respuesta += ' Actividades relacionadas: ' + ', '.join(nombres[:3]) + '.'
        respuesta += ' Los avisos de mantenimiento describen el estado actual del inventario.'
        return respuesta, datos, ['reservas', 'espacios', '/api/alertas/']

    raise PreguntaNoReconocida('Esa consulta no está disponible. Elegí uno de los ejemplos.')
