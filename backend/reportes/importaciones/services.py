from django.db import connection, transaction

from espacios.models import Aula, Categoria, Equipamiento
from espacios.serializers import AulaSerializer, EquipamientoSerializer


def _booleano(valor):
    if isinstance(valor, bool):
        return valor
    texto = str(valor).strip().casefold()
    if texto in ('1', 'true', 'si', 'sí'):
        return True
    if texto in ('0', 'false', 'no'):
        return False
    raise ValueError('Usá true/false, 1/0 o sí/no.')


def _preparar_datos(tipo, datos):
    datos = {k: v.strip() if isinstance(v, str) else v for k, v in datos.items()}
    errores = {}
    requeridos = ['nombre', 'capacidad'] if tipo == 'aulas' else ['nombre', 'categoria', 'cantidad', 'trasladable']
    for campo in requeridos:
        if campo not in datos or datos[campo] is None or datos[campo] == '':
            errores[campo] = ['Este campo es obligatorio.']
    if errores or tipo == 'aulas':
        return datos, errores

    try:
        datos['trasladable'] = _booleano(datos['trasladable'])
    except ValueError as exc:
        errores['trasladable'] = [str(exc)]
    for campo, modelo in [('categoria', Categoria), ('aula', Aula)]:
        valor = datos.get(campo)
        if valor is None or valor == '':
            datos.pop(campo, None)
            continue
        relacion = modelo.objects.filter(nombre=str(valor)).first()
        if relacion is None:
            errores[campo] = ['No existe un registro con ese nombre exacto.']
        else:
            datos[campo] = relacion.pk
    return datos, errores


def _coincidencias(tipo, datos):
    if tipo == 'aulas':
        return Aula.objects.filter(nombre=datos.get('nombre')).order_by('pk')
    return Equipamiento.objects.filter(
        nombre=datos.get('nombre'), categoria_id=datos.get('categoria'),
        aula_id=datos.get('aula'), trasladable=datos.get('trasladable'),
    ).order_by('pk')


def _validar_filas(tipo, filas):
    planes, identidades = [], {}
    clase_serializer = AulaSerializer if tipo == 'aulas' else EquipamientoSerializer
    for fila in filas:
        resultado = {'fila': fila['fila'], 'accion': 'error'}
        planes.append(resultado)
        datos, errores = _preparar_datos(tipo, fila['datos'])
        if errores:
            resultado['errores'] = errores
            continue
        coincidencias = list(_coincidencias(tipo, datos)[:2])
        if len(coincidencias) > 1:
            resultado['errores'] = {'nombre': ['Existen varias coincidencias; revisá el catálogo antes de importar.']}
            continue
        existente = coincidencias[0] if coincidencias else None
        serializer = clase_serializer(existente, data=datos, partial=existente is not None)
        if not serializer.is_valid():
            resultado['errores'] = dict(serializer.errors)
            continue
        validados = serializer.validated_data
        identidad = (validados['nombre'],) if tipo == 'aulas' else (
            validados['nombre'], validados['categoria'].pk,
            validados['aula'].pk if validados.get('aula') else None, validados['trasladable'],
        )
        if identidad in identidades:
            anterior = identidades[identidad]
            resultado['errores'] = {'duplicado': [f"Repite el registro de la fila {anterior['fila']}."]}
            anterior['accion'] = 'error'
            anterior['errores'] = {'duplicado': [f"Repite el registro de la fila {fila['fila']}."]}
            continue
        identidades[identidad] = resultado
        if existente:
            distintos = [campo for campo, valor in validados.items() if getattr(existente, campo) != valor]
            if distintos:
                resultado['errores'] = {campo: ['El registro existente tiene otro valor; esta carga no actualiza datos.']
                                        for campo in distintos}
                continue
            resultado.update(accion='omitir', id=existente.pk)
        else:
            resultado.update(accion='crear', _serializer=serializer)
    return planes


def procesar_importacion(tipo, filas, confirmar=False):
    if tipo not in ('aulas', 'equipamientos'):
        raise ValueError('Tipo de catálogo no admitido.')
    with transaction.atomic():
        if confirmar and connection.vendor == 'postgresql':
            # Serializa las cargas de este módulo, incluso con catálogos vacíos.
            # No requiere cambiar modelos ni restricciones de los catálogos.
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [58216001])
        planes = _validar_filas(tipo, filas)
        errores = sum(f['accion'] == 'error' for f in planes)
        creadas = 0
        if confirmar and not errores:
            for fila in planes:
                if fila['accion'] == 'crear':
                    instancia = fila['_serializer'].save()
                    fila['id'] = instancia.pk
                    creadas += 1
        return {
            'recurso': tipo, 'modo': 'importacion' if confirmar else 'validacion',
            'resumen': {
                'filas': len(planes), 'por_crear': sum(f['accion'] == 'crear' for f in planes),
                'omitidas': sum(f['accion'] == 'omitir' for f in planes),
                'creadas': creadas, 'errores': errores,
            },
            'filas': [{k: v for k, v in fila.items() if k != '_serializer'} for fila in planes],
        }
