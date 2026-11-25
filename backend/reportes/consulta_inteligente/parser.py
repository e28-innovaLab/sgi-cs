"""Interpretación local y acotada; devuelve planes de lectura, nunca SQL."""

from datetime import date, time, timedelta
import re
import unicodedata

from django.utils import timezone


class PreguntaNoReconocida(ValueError):
    """La pregunta necesita aclaración o está fuera de las consultas admitidas."""


def _normalizar(texto):
    if not isinstance(texto, str) or not texto.strip():
        raise PreguntaNoReconocida('Escribí una pregunta sobre aulas, reservas, equipos o alertas.')
    return ' '.join(''.join(
        caracter for caracter in unicodedata.normalize('NFKD', texto.lower())
        if not unicodedata.combining(caracter)
    ).split())


def _fecha_iso(valor):
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise PreguntaNoReconocida('La fecha no es válida. Usá el formato YYYY-MM-DD.') from exc


def _periodo(texto, hoy, *, alertas=False, disponibilidad=False):
    fechas = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', texto)
    periodos = re.findall(r'\beste mes\b|\bmes pasado\b|\besta semana\b|\bultimos?\s+\d+\s+dias?\b', texto)
    if len(periodos) > 1 or fechas and periodos:
        raise PreguntaNoReconocida('Indicá un solo período por pregunta.')
    rango = re.search(r'\bdesde\s+(\d{4}-\d{2}-\d{2})\s+(?:hasta|al)\s+(\d{4}-\d{2}-\d{2})\b', texto)
    if rango:
        if len(fechas) != 2:
            raise PreguntaNoReconocida('Indicá un solo período para la consulta.')
        desde, hasta = map(_fecha_iso, rango.groups())
    elif len(fechas) == 1:
        if re.search(r'\b(desde|hasta)\b', texto):
            raise PreguntaNoReconocida('Completá el período: desde YYYY-MM-DD hasta YYYY-MM-DD.')
        desde = hasta = _fecha_iso(fechas[0])
    elif fechas:
        raise PreguntaNoReconocida('Escribí el período como desde YYYY-MM-DD hasta YYYY-MM-DD.')
    elif re.search(r'\b\d{1,2}/\d{1,2}|\b\d{4}-|\b(?:19|20)\d{2}\b', texto):
        raise PreguntaNoReconocida('Usá fechas YYYY-MM-DD o expresiones como hoy, mañana o este mes.')
    elif 'este mes' in texto:
        desde, hasta = hoy.replace(day=1), hoy
    elif 'mes pasado' in texto:
        hasta = hoy.replace(day=1) - timedelta(days=1)
        desde = hasta.replace(day=1)
    elif 'esta semana' in texto:
        desde, hasta = hoy - timedelta(days=hoy.weekday()), hoy
    elif re.search(r'\bultimos?\s+\d+\s+dias?\b', texto):
        dias = int(re.search(r'\bultimos?\s+(\d+)\s+dias?\b', texto).group(1))
        if not 1 <= dias <= 366:
            raise PreguntaNoReconocida('Elegí un período de entre 1 y 366 días.')
        desde, hasta = hoy - timedelta(days=dias - 1), hoy
    else:
        if 'por la manana' in texto or 'por la tarde' in texto or 'por la noche' in texto:
            raise PreguntaNoReconocida('Indicá la fecha y horas concretas, por ejemplo mañana de 14 a 16.')
        relativas = [
            (r'\bpasado manana\b', 2), (r'\banteayer\b', -2),
            (r'\bmanana\b', 1), (r'\bayer\b', -1), (r'\bhoy\b', 0),
        ]
        encontrada = None
        resto = texto
        for patron, diferencia in relativas:
            if re.search(patron, resto):
                if encontrada is not None:
                    raise PreguntaNoReconocida('Indicá una fecha o un período sin expresiones contradictorias.')
                encontrada = hoy + timedelta(days=diferencia)
                resto = re.sub(patron, '', resto)
        if encontrada is not None:
            desde = hasta = encontrada
        elif re.search(r'\b(proxim[oa]|pasad[oa]|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b', texto):
            raise PreguntaNoReconocida('Indicá una fecha YYYY-MM-DD o un período como este mes.')
        elif disponibilidad:
            desde = hasta = hoy
        elif alertas:
            desde, hasta = hoy, hoy + timedelta(days=29)
        else:
            desde, hasta = hoy - timedelta(days=29), hoy
    if desde > hasta:
        raise PreguntaNoReconocida('La fecha inicial debe ser igual o anterior a la final.')
    if (hasta - desde).days >= 366:
        raise PreguntaNoReconocida('Elegí un período de hasta 366 días inclusivos.')
    return desde, hasta


def _horario(texto):
    valor = r'(\d{1,2}(?::\d{2})?)'
    match = re.search(r'\b(?:de|desde)\s+' + valor + r'\s+(?:a|hasta)\s+' + valor + r'(?![\d:])', texto)
    if match is None:
        match = re.search(r'\bentre\s+' + valor + r'\s+y\s+' + valor + r'(?![\d:])', texto)
    if match is None:
        match = re.search(r'(?<![\d-])\b' + valor + r'\s*[-–]\s*' + valor + r'(?![\d:-])', texto)
    if match is None:
        raise PreguntaNoReconocida('Indicá el horario: por ejemplo mañana de 10 a 12.')
    horas = []
    try:
        for valor in match.groups():
            partes = valor.split(':')
            horas.append(time(int(partes[0]), int(partes[1]) if len(partes) == 2 else 0))
    except ValueError as exc:
        raise PreguntaNoReconocida('Usá horas válidas entre 00:00 y 23:59.') from exc
    if horas[0] >= horas[1]:
        raise PreguntaNoReconocida('La hora final debe ser posterior a la inicial, dentro del mismo día.')
    return horas


def interpretar_pregunta(pregunta, hoy=None):
    """Reconoce cinco consultas previstas; no intenta adivinar preguntas generales."""
    texto = _normalizar(pregunta)
    hoy = hoy or timezone.localdate()
    if re.search(r'\b(borra\w*|elimina\w*|modifica\w*|actualiza\w*|crea\w*|cancel(?:a|ar|e|en)|confirm(?:a|ar|e|en)|insert|select|update|delete|drop|alter|sql|ignora\w*|omite\w*|instruccion\w*|contrasena\w*|password|token\w*|dni|documento\w*|correo\w*|email\w*|domicilio\w*|telefono\w*|celular\w*|nombres?|apellidos?)\b', texto):
        raise PreguntaNoReconocida('Solo puedo consultar información operativa agregada; no modifico datos ni muestro datos personales.')
    if re.search(r'\b(no|excepto|distint[oa]s?)\b', texto):
        raise PreguntaNoReconocida('Por ahora no interpreto negaciones ni exclusiones. Reformulá la consulta indicando directamente el estado o dato que buscás.')

    if re.search(r'\b(usuario|persona|responsable|solicitante|portatiles?|fijos?|trasladables?|notebooks?|proyectores?|simuladores?|computadoras?)\b|["\']', texto):
        raise PreguntaNoReconocida('Por ahora no filtro por personas ni por nombres o características de recursos. Reformulá la consulta en términos generales.')
    nombre_recurso = re.search(
        r'\b(?:aula|laboratorio|taller|equipo|recurso)\s+(?!(?:disponible|libre|con|de|para|que|tuvo|tiene|esta|mas|menos|mayor|menor|en|el|la|este|ayer|hoy|manana|ocupacion|utilizacion|uso|demanda)\b)(\w+)', texto,
    )
    persona_reserva = re.search(
    r'\breservas?\s+(?:de|para)\s+(?!\d)'
    r'(?!(?:este|esta|hoy|ayer|manana|los|las|un|una|el|la|mes|semana|'
    r'aulas?|espacios?|laboratorios?|taller(?:es)?|equipos?|equipamiento|recursos?)\b)'
    r'(\w+)',
    texto
    )
    if nombre_recurso or persona_reserva:
        raise PreguntaNoReconocida('No reconozco ese filtro por nombre. Preguntá por aulas, espacios o equipos en general.')

    espacio = bool(re.search(r'\b(aulas?|espacios?|laboratorios?|taller(?:es)?)\b', texto))
    equipo = bool(re.search(r'\b(equipos?|equipamiento|recursos?|notebooks?)\b', texto))
    disponibilidad = bool(re.search(r'\b(disponibles?|disponibilidad|libres?)\b', texto))
    uso = bool(re.search(r'\b(ocupacion|utilizacion|uso|demanda|solicitados?)\b', texto))
    alerta = bool(re.search(r'\b(alertas?|conflictos?|faltantes?|pendientes?|problemas?|vencidas?)\b|\bsin (?:aula|espacio|equipamiento)', texto))
    resumen = bool(re.search(r'\breservas?\b', texto) and re.search(r'\b(cuantas?|cuantos?|resumen|total|cantidad|hubo|hay|tenemos|registradas?)\b', texto))
    estados = [valor for patron, valor in [
        (r'\bconfirmad[ao]s?\b', 'Confirmada'), (r'\bcancelad[ao]s?\b', 'Cancelada'),
        (r'\bpendientes?\b', 'Pendiente'), (r'\bfinalizad[ao]s?\b', 'Finalizada'),
        (r'\brechazad[ao]s?\b', 'Rechazada'),
    ] if re.search(patron, texto)]
    if len(estados) > 1:
        raise PreguntaNoReconocida('Consultá un solo estado por pregunta.')
    if (disponibilidad and (uso or resumen or estados) or uso and resumen
            or alerta and uso or uso and equipo and espacio):
        raise PreguntaNoReconocida('Hacé una sola consulta por pregunta: disponibilidad, reservas, utilización o alertas.')
    if resumen and re.search(r'\bpara\s+\d+\s+(?:personas?|participantes?)\b', texto):
        raise PreguntaNoReconocida('El filtro de capacidad solo está disponible para consultar aulas disponibles.')

    if disponibilidad:
        if equipo or not espacio:
            raise PreguntaNoReconocida('Por ahora consulto disponibilidad de aulas; para equipos puedo informar utilización o demanda.')
        desde, hasta = _periodo(texto, hoy, disponibilidad=True)
        if desde != hasta:
            raise PreguntaNoReconocida('Para disponibilidad indicá un único día y un horario.')
        inicio, fin = _horario(texto)
        parametros = {'fecha': desde, 'hora_inicio': inicio, 'hora_fin': fin}
        capacidad = re.search(
            r'\bpara\s+(-?\d+)\s+(?:personas?|participantes?|plazas?)\b'
            r'|\bcapacidad(?: minima)?(?: de)?\s+(-?\d+)(?![\d:.,/-])\b', texto,
        )
        if capacidad:
            cantidad = int(next(valor for valor in capacidad.groups() if valor is not None))
            if cantidad < 1:
                raise PreguntaNoReconocida('La capacidad solicitada debe ser mayor que cero.')
            parametros['capacidad_min'] = cantidad
        elif (re.search(r'\bcapacidad\b', texto)
              or re.search(r'\bpara\s+-?\d+\b', texto)
              and not re.search(r'\bpara\s+\d{4}-\d{2}-\d{2}\b', texto)):
            raise PreguntaNoReconocida('Para indicar capacidad escribí, por ejemplo, para 20 personas.')
        if re.search(r'\blaboratorios?\b', texto):
            parametros['tipo_aula'] = 'LABORATORIO'
        elif re.search(r'\btaller(?:es)?\b', texto):
            parametros['tipo_aula'] = 'TALLER'
        elif re.search(r'\baulas?\b', texto):
            parametros['tipo_aula'] = 'AULA'
        return {'intencion': 'disponibilidad_aulas', 'parametros': parametros}

    if (re.search(r'\b(laboratorios?|taller(?:es)?)\b', texto)
            or uso and re.search(r'\baulas?\b', texto)):
        raise PreguntaNoReconocida('El filtro por tipo de espacio solo está disponible en disponibilidad. Para consultar ocupación general, usá espacios.')

    if resumen:
        intencion, extras = 'resumen_reservas', {}
    elif alerta:
        if re.search(r'\b(cuantas?|cuantos?|cantidad|total)\b', texto):
            raise PreguntaNoReconocida('Puedo listar alertas; probá: ¿Qué actividades tienen equipamiento pendiente mañana?')
        intencion = 'alertas_operativas'
        extras = {'tema': 'equipamiento' if equipo else 'espacios' if espacio else 'todas'}
    elif uso and (equipo or espacio):
        intencion = 'utilizacion_equipos' if equipo else 'utilizacion_espacios'
        extras = {'orden': 'asc' if re.search(r'\b(menor|menos|baja)\b', texto) else 'desc'}
        if equipo:
            extras['metrica'] = 'demanda' if re.search(r'\b(demanda|solicitados?)\b', texto) else 'utilizacion'
    else:
        raise PreguntaNoReconocida('No reconocí esa consulta. Probá con reservas, ocupación de espacios, uso de equipos, aulas disponibles o alertas.')

    if re.search(r'\b(?:de|entre)\s+\d{1,2}(?::\d{2})?\s+(?:a|y)\s+\d{1,2}', texto):
        raise PreguntaNoReconocida('El filtro por horas solo está disponible para consultar aulas disponibles.')
    desde, hasta = _periodo(texto, hoy, alertas=intencion == 'alertas_operativas')
    if estados and intencion != 'alertas_operativas':
        extras['estado'] = estados[0]
    return {'intencion': intencion, 'parametros': {'desde': desde, 'hasta': hasta, **extras}}
