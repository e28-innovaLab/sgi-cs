from datetime import datetime
from django.utils import timezone

from usuarios.models import Rol, Usuario
from usuarios.permissions import es_administrador

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum

from espacios.models import Aula, Equipamiento
from .models import (
    Reserva,
    ReservaAula,
    SolicitudEquipo,
    EstadoReserva,
    UsuarioPorReserva,
    Participante,
    ReservaParticipante,
)


ESTADOS_QUE_BLOQUEAN = [
    EstadoReserva.Estados.PENDIENTE,
    EstadoReserva.Estados.CONFIRMADA,
]


def obtener_aulas_disponibles(fecha, hora_inicio, hora_fin):
    """
    Devuelve las aulas disponibles para una fecha y un horario.
    Las reservas pendientes y confirmadas bloquean el aula.
    """

    if hora_inicio >= hora_fin:
        raise ValueError(
            "La hora de fin debe ser posterior a la hora de inicio."
        )

    asignaciones_ocupadas = ReservaAula.objects.filter(
        reserva__fecha_reserva=fecha,
        reserva__estado_reserva__estado__in=ESTADOS_QUE_BLOQUEAN,
        reserva__horario_inicio__lt=hora_fin,
        reserva__horario_fin__gt=hora_inicio,
    )

    aulas_ocupadas = asignaciones_ocupadas.values_list(
        "aula_id",
        flat=True,
    )

    return Aula.objects.filter(estado=Aula.Estado.DISPONIBLE).exclude(
        pk__in=aulas_ocupadas
    ).order_by("nombre")


def _asociar_equipamiento_fijo_disponible(reserva, aulas):
    """
    Asocia automáticamente los equipamientos fijos disponibles
    pertenecientes a las aulas indicadas.
    """
    for aula in aulas:

        # Bloqueamos los equipamientos fijos disponibles del aula.
        equipamientos = (
            Equipamiento.objects
            .select_for_update()
            .filter(
                aula=aula,
                trasladable=False,
                estado=Equipamiento.Estado.DISPONIBLE,
            )
            .order_by("pk")
        )

        # Consultamos la disponibilidad una sola vez por aula.
        disponibilidad = obtener_equipamiento_disponible(
            fecha=reserva.fecha_reserva,
            hora_inicio=reserva.horario_inicio,
            hora_fin=reserva.horario_fin,
            aulas=[aula],
            excluir_reserva_id=reserva.pk,
        )

        for equipo in equipamientos:

            # Si ya existe una solicitud, no se duplica ni se modifica.
            solicitud_existente = SolicitudEquipo.objects.filter(
                reserva=reserva,
                equipamiento=equipo,
            ).exists()

            if solicitud_existente:
                continue

            item = next(
                (
                    elemento
                    for elemento in disponibilidad
                    if elemento["equipamiento"].pk == equipo.pk
                ),
                None,
            )

            # Si no hay stock disponible, se omite el equipamiento.
            if item is None:
                continue

            cantidad = item["cantidad_disponible"]

            solicitud = SolicitudEquipo(
                reserva=reserva,
                equipamiento=equipo,
                cantidad_solicitada=cantidad,
                cantidad_reservada=cantidad,
                cantidad_critica=1,
                asignacion_automatica=True,
            )

            solicitud.full_clean()
            solicitud.save()


def quitar_aula_reserva(reserva_id, aula_id):
    """
    Quita un aula de una reserva si no tiene solicitudes
    de equipamiento fijo asociadas y la capacidad restante
    es suficiente para los participantes.
    """

    with transaction.atomic():

        # Bloqueamos la reserva.
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva indicada no existe."
            )

        # Bloqueamos el aula.
        try:
            aula = Aula.objects.select_for_update().get(
                pk=aula_id
            )
        except Aula.DoesNotExist:
            raise ValidationError(
                "El aula indicada no existe."
            )

        # Comprobamos que el aula esté asociada a la reserva.
        try:
            reserva_aula = ReservaAula.objects.select_for_update().get(
                reserva=reserva,
                aula=aula,
            )
        except ReservaAula.DoesNotExist:
            raise ValidationError(
                "El aula indicada no está asociada a esta reserva."
            )

        # Comprobamos si existen solicitudes de equipamiento fijo
        # pertenecientes al aula que queremos quitar.
        solicitudes_fijas = SolicitudEquipo.objects.filter(
            reserva=reserva,
            equipamiento__aula=aula,
            equipamiento__trasladable=False,
        )

        if solicitudes_fijas.exists():
            raise ValidationError(
                "No se puede quitar el aula porque tiene solicitudes "
                "de equipamiento fijo asociadas. Primero debe eliminar "
                "esas solicitudes."
            )

        # Calculamos la capacidad de las aulas restantes.
        aulas_restantes_ids = ReservaAula.objects.filter(
            reserva=reserva,
        ).exclude(
            aula=aula,
        ).values_list(
            "aula_id",
            flat=True,
        )

        capacidad_restante = Aula.objects.filter(
            pk__in=aulas_restantes_ids,
        ).aggregate(
            total=Sum("capacidad")
        )["total"] or 0

        # Contamos los participantes de la reserva.
        cantidad_participantes = ReservaParticipante.objects.filter(
            reserva=reserva,
        ).count()

        if capacidad_restante < cantidad_participantes:
            raise ValidationError(
                "No se puede quitar el aula porque la capacidad "
                "de las aulas restantes sería insuficiente "
                "para los participantes."
            )

        # Eliminamos la asociación.
        reserva_aula.delete()

    # Devolvemos las aulas que siguen asociadas.
    return [
        relacion.aula
        for relacion in ReservaAula.objects.filter(
            reserva=reserva,
        ).select_related("aula").order_by("aula_id")
    ]


def asignar_aulas_reserva(reserva_id, aulas_ids):
    """
    Agrega aulas a una reserva y asocia automáticamente
    sus equipamientos fijos disponibles.
    """

    aulas_ids = sorted(set(aulas_ids))

    if not aulas_ids:
        raise ValidationError(
            "Debe seleccionar al menos un aula."
        )

    with transaction.atomic():

        # Bloqueamos la reserva.
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva indicada no existe."
            )

        # Bloqueamos las aulas seleccionadas.
        aulas = list(
            Aula.objects.select_for_update().filter(
                pk__in=aulas_ids,
                estado=Aula.Estado.DISPONIBLE,
            ).order_by("pk")
        )

        if len(aulas) != len(aulas_ids):
            raise ValidationError(
                "Una o más aulas no existen o no están disponibles."
            )

        # Recuperamos las aulas que ya tiene la reserva.
        aulas_existentes_ids = set(
            ReservaAula.objects.filter(
                reserva=reserva,
            ).values_list("aula_id", flat=True)
        )

        # Solo agregamos las aulas que todavía no están asociadas.
        nuevas_aulas = [
            aula for aula in aulas
            if aula.pk not in aulas_existentes_ids
        ]

        # Comprobamos disponibilidad de las nuevas aulas.
        asignaciones_ocupadas = ReservaAula.objects.filter(
            aula_id__in=[aula.pk for aula in nuevas_aulas],
            reserva__fecha_reserva=reserva.fecha_reserva,
            reserva__estado_reserva__estado__in=ESTADOS_QUE_BLOQUEAN,
            reserva__horario_inicio__lt=reserva.horario_fin,
            reserva__horario_fin__gt=reserva.horario_inicio,
        ).exclude(
            reserva_id=reserva.pk,
        )

        if asignaciones_ocupadas.exists():
            raise ValidationError(
                "Una o más aulas ya están ocupadas "
                "en ese día y horario."
            )

        # Calculamos la capacidad total de todas las aulas.
        capacidad_total = Aula.objects.filter(
            pk__in=aulas_existentes_ids.union(aulas_ids)
        ).aggregate(
            total=Sum("capacidad")
        )["total"] or 0

        cantidad_participantes = ReservaParticipante.objects.filter(
            reserva=reserva,
        ).count()

        if capacidad_total < cantidad_participantes:
            raise ValidationError(
                "La capacidad total de las aulas seleccionadas "
                "no puede ser menor que la cantidad de participantes."
            )

        # Comprobamos que no se quiten aulas que tengan
        # solicitudes de equipamiento fijo asociadas.
        solicitudes_fijas = SolicitudEquipo.objects.filter(
            reserva=reserva,
            equipamiento__trasladable=False,
        ).select_related("equipamiento")

        aulas_necesarias = {
            solicitud.equipamiento.aula_id
            for solicitud in solicitudes_fijas
        }

        aulas_resultantes_ids = aulas_existentes_ids.union(aulas_ids)

        if not aulas_necesarias.issubset(aulas_resultantes_ids):
            raise ValidationError(
                "No se pueden quitar aulas que tengan solicitudes "
                "de equipamiento fijo asociadas."
            )

        # Agregamos las nuevas aulas sin eliminar las anteriores.
        ReservaAula.objects.bulk_create([
            ReservaAula(
                reserva=reserva,
                aula=aula,
            )
            for aula in nuevas_aulas
        ])

        # Asociamos automáticamente los equipamientos fijos disponibles.
        _asociar_equipamiento_fijo_disponible(
            reserva,
            nuevas_aulas,
        )

    return [
        relacion.aula
        for relacion in ReservaAula.objects.filter(
            reserva=reserva,
        ).select_related("aula").order_by("aula_id")
    ]


def obtener_equipamiento_disponible(
    fecha,
    hora_inicio,
    hora_fin,
    aulas,
    excluir_reserva_id=None,
):
    """
    Devuelve los equipamientos disponibles y sus cantidades
    para una fecha, horario y conjunto de aulas.

    Permite excluir una reserva existente de la consulta.
    """

    if hora_inicio >= hora_fin:
        raise ValidationError(
            "La hora de fin debe ser posterior a la hora de inicio."
        )

    aula_ids = [
        aula.pk if isinstance(aula, Aula) else aula
        for aula in aulas
    ]

    equipamientos = Equipamiento.objects.filter(
        estado=Equipamiento.Estado.DISPONIBLE,
    )

    resultado = []

    for equipo in equipamientos:

        if equipo.trasladable:
            solicitudes_ocupadas = SolicitudEquipo.objects.filter(
                equipamiento=equipo,
                reserva__fecha_reserva=fecha,
                reserva__estado_reserva__estado__in=ESTADOS_QUE_BLOQUEAN,
                reserva__horario_inicio__lt=hora_fin,
                reserva__horario_fin__gt=hora_inicio,
            )

            if excluir_reserva_id is not None:
                solicitudes_ocupadas = solicitudes_ocupadas.exclude(
                    reserva_id=excluir_reserva_id,
                )

        else:
            if equipo.aula_id not in aula_ids:
                continue

            reservas_del_aula = ReservaAula.objects.filter(
                aula_id=equipo.aula_id,
                reserva__fecha_reserva=fecha,
                reserva__estado_reserva__estado__in=ESTADOS_QUE_BLOQUEAN,
                reserva__horario_inicio__lt=hora_fin,
                reserva__horario_fin__gt=hora_inicio,
            ).values_list(
                "reserva_id",
                flat=True,
            ).distinct()

            if excluir_reserva_id is not None:
                reservas_del_aula = reservas_del_aula.exclude(
                    reserva_id=excluir_reserva_id,
                )

            solicitudes_ocupadas = SolicitudEquipo.objects.filter(
                equipamiento=equipo,
                reserva_id__in=reservas_del_aula,
            )

        cantidad_comprometida = 0

        for solicitud in solicitudes_ocupadas:
            if solicitud.cantidad_reservada is not None:
                cantidad_comprometida += solicitud.cantidad_reservada
            else:
                cantidad_comprometida += solicitud.cantidad_solicitada

        cantidad_disponible = equipo.cantidad - cantidad_comprometida

        if cantidad_disponible > 0:
            resultado.append({
                "equipamiento": equipo,
                "cantidad_total": equipo.cantidad,
                "cantidad_disponible": cantidad_disponible,
            })

    return resultado


def validar_solicitante_reserva(reserva):
    """
    Verifica que una reserva tenga exactamente un usuario solicitante.
    """

    cantidad_solicitantes = UsuarioPorReserva.objects.filter(
        reserva=reserva,
        solicitante=True,
    ).count()

    if cantidad_solicitantes != 1:
        raise ValidationError(
            "Para confirmar la reserva debe existir exactamente "
            "un usuario solicitante."
        )


@transaction.atomic
def asociar_usuario_reserva(reserva_id, usuario_id, solicitante=False):
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)

    usuario = Usuario.objects.get(pk=usuario_id)

    if reserva.estado_reserva.estado != EstadoReserva.Estados.PENDIENTE:
        raise ValidationError(
            "Solo se pueden asociar usuarios a reservas pendientes."
        )

    # Si será el solicitante, primero quitamos esa condición al anterior.
    if solicitante:
        UsuarioPorReserva.objects.filter(
            reserva=reserva,
            solicitante=True,
        ).update(solicitante=False)

    asociacion, creada = UsuarioPorReserva.objects.get_or_create(
        reserva=reserva,
        usuario=usuario,
        defaults={"solicitante": solicitante},
    )

    # Si ya estaba asociado, actualizamos su condición de solicitante.
    if not creada and solicitante:
        asociacion.solicitante = True
        asociacion.save(update_fields=["solicitante"])

    return asociacion


@transaction.atomic
def cambiar_solicitante_reserva(reserva_id, usuario_id):
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)

    if reserva.estado_reserva.estado != EstadoReserva.Estados.PENDIENTE:
        raise ValidationError(
            "Solo se puede cambiar el solicitante de una reserva pendiente."
        )

    asociacion = UsuarioPorReserva.objects.select_for_update().filter(
        reserva=reserva,
        usuario_id=usuario_id,
    ).first()

    if not asociacion:
        raise ValidationError(
            "El usuario debe estar asociado a la reserva para ser solicitante."
        )

    UsuarioPorReserva.objects.filter(
        reserva=reserva,
        solicitante=True,
    ).update(solicitante=False)

    asociacion.solicitante = True
    asociacion.save(update_fields=["solicitante"])

    return asociacion


@transaction.atomic
def eliminar_usuario_reserva(reserva_id, usuario_id):
    reserva = Reserva.objects.select_for_update().get(pk=reserva_id)

    if reserva.estado_reserva.estado != EstadoReserva.Estados.PENDIENTE:
        raise ValidationError(
            "Solo se pueden quitar usuarios de reservas pendientes."
        )

    asociacion = UsuarioPorReserva.objects.select_for_update().filter(
        reserva=reserva,
        usuario_id=usuario_id,
    ).first()

    if not asociacion:
        raise ValidationError(
            "El usuario no está asociado a esta reserva."
        )

    if asociacion.solicitante:
        raise ValidationError(
            "No se puede quitar al solicitante de la reserva. "
            "Primero debe asignarse otro solicitante."
        )

    asociacion.delete()



def solicitar_equipamiento_reserva(
    reserva_id,
    equipamiento_id,
    cantidad_solicitada,
    cantidad_critica,
):
    """
    Crea o actualiza una solicitud expresa de equipamiento.

    Si el equipamiento es fijo, asocia automáticamente su aula
    a la reserva cuando todavía no está asociada.

    Comprueba la disponibilidad y compromete el stock dentro
    de una transacción.
    """

    with transaction.atomic():

        # Bloqueamos la reserva.
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva indicada no existe."
            )

        # Solo las reservas pendientes o confirmadas pueden
        # comprometer equipamiento.
        if (
            reserva.estado_reserva is None
            or reserva.estado_reserva.estado not in ESTADOS_QUE_BLOQUEAN
        ):
            raise ValidationError(
                "Solo se puede solicitar equipamiento para "
                "reservas pendientes o confirmadas."
            )

        # Bloqueamos el equipamiento.
        try:
            equipamiento = Equipamiento.objects.select_for_update().get(
                pk=equipamiento_id
            )
        except Equipamiento.DoesNotExist:
            raise ValidationError(
                "El equipamiento indicado no existe."
            )

        if equipamiento.estado != Equipamiento.Estado.DISPONIBLE:
            raise ValidationError(
                "El equipamiento seleccionado no está disponible."
            )

        # Si el equipamiento es fijo, asociamos su aula
        # automáticamente cuando todavía no pertenece a la reserva.
        if not equipamiento.trasladable:

            if equipamiento.aula_id is None:
                raise ValidationError(
                    "El equipamiento fijo no tiene un aula asignada."
                )

            aula_ya_asociada = reserva.aulas.filter(
                pk=equipamiento.aula_id
            ).exists()

            if not aula_ya_asociada:
                asignar_aulas_reserva(
                    reserva_id=reserva.pk,
                    aulas_ids=[equipamiento.aula_id],
                )

        # Buscamos si ya existe una solicitud de este equipo.
        # Puede ser una solicitud automática creada al asociar el aula.
        solicitud = SolicitudEquipo.objects.filter(
            reserva=reserva,
            equipamiento=equipamiento,
        ).first()

        # Consultamos la disponibilidad excluyendo la propia
        # reserva, para no contar su solicitud anterior dos veces.
        aulas = list(reserva.aulas.all())

        equipamientos_disponibles = obtener_equipamiento_disponible(
            fecha=reserva.fecha_reserva,
            hora_inicio=reserva.horario_inicio,
            hora_fin=reserva.horario_fin,
            aulas=aulas,
            excluir_reserva_id=reserva.pk,
        )

        disponibilidad = next(
            (
                item
                for item in equipamientos_disponibles
                if item["equipamiento"].pk == equipamiento.pk
            ),
            None,
        )

        cantidad_disponible = (
            disponibilidad["cantidad_disponible"]
            if disponibilidad is not None
            else 0
        )

        if cantidad_disponible <= 0:
            raise ValidationError(
                "No hay unidades disponibles de este equipamiento."
            )

        cantidad_reservada = min(
            cantidad_solicitada,
            cantidad_disponible,
        )

        # Creamos o actualizamos la solicitud.
        if solicitud is None:
            solicitud = SolicitudEquipo(
                reserva=reserva,
                equipamiento=equipamiento,
            )

        solicitud.cantidad_solicitada = cantidad_solicitada
        solicitud.cantidad_reservada = cantidad_reservada
        solicitud.cantidad_critica = cantidad_critica

        # Al solicitarlo expresamente, deja de ser automática.
        solicitud.asignacion_automatica = False

        # Ejecutamos las validaciones definidas en el modelo.
        solicitud.full_clean()

        solicitud.save()

    return solicitud


def actualizar_solicitud_equipamiento(
    solicitud_id,
    equipamiento_id,
    cantidad_solicitada,
    cantidad_critica,
):
    """
    Actualiza una solicitud de equipamiento existente.

    Permite cambiar el equipamiento y las cantidades,
    manteniendo la reserva original.

    Si existe una solicitud automática para el nuevo equipamiento,
    la convierte en manual y elimina la solicitud anterior.
    """

    with transaction.atomic():

        # Bloqueamos la solicitud existente.
        try:
            solicitud_actual = (
                SolicitudEquipo.objects
                .select_for_update()
                .get(pk=solicitud_id)
            )
        except SolicitudEquipo.DoesNotExist:
            raise ValidationError(
                "La solicitud de equipamiento no existe."
            )

        # No permitimos modificar solicitudes automáticas.
        if solicitud_actual.asignacion_automatica:
            raise ValidationError(
                "No se pueden modificar solicitudes de equipamiento "
                "asignadas automáticamente."
            )

        # Bloqueamos la reserva original.
        try:
            reserva = (
                Reserva.objects
                .select_for_update(of=("self",))
                .select_related("estado_reserva")
                .get(pk=solicitud_actual.reserva_id)
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva asociada no existe."
            )

        # Verificamos que la reserva permita solicitar equipamiento.
        if (
            reserva.estado_reserva is None
            or reserva.estado_reserva.estado not in ESTADOS_QUE_BLOQUEAN
        ):
            raise ValidationError(
                "Solo se puede modificar equipamiento de reservas "
                "pendientes o confirmadas."
            )

        # Bloqueamos el nuevo equipamiento.
        try:
            equipamiento = (
                Equipamiento.objects
                .select_for_update()
                .get(pk=equipamiento_id)
            )
        except Equipamiento.DoesNotExist:
            raise ValidationError(
                "El equipamiento indicado no existe."
            )

        # Verificamos que el equipamiento esté disponible.
        if equipamiento.estado != Equipamiento.Estado.DISPONIBLE:
            raise ValidationError(
                "El equipamiento seleccionado no está disponible."
            )

        # Si es fijo, su aula debe estar asociada a la reserva.
        if not equipamiento.trasladable:

            if equipamiento.aula_id is None:
                raise ValidationError(
                    "El equipamiento fijo no tiene un aula asignada."
                )

            if not reserva.aulas.filter(
                pk=equipamiento.aula_id
            ).exists():
                raise ValidationError(
                    "El aula del equipamiento fijo debe estar "
                    "asociada previamente a la reserva."
                )

        # Validamos que no exista otra solicitud manual
        # para el mismo equipamiento y reserva.
        otra_solicitud = (
            SolicitudEquipo.objects
            .select_for_update()
            .filter(
                reserva=reserva,
                equipamiento=equipamiento,
            )
            .exclude(pk=solicitud_actual.pk)
            .first()
        )

        if (
            otra_solicitud is not None
            and not otra_solicitud.asignacion_automatica
        ):
            raise ValidationError(
                "Ya existe una solicitud manual para ese equipamiento "
                "en esta reserva."
            )

        # Consultamos la disponibilidad excluyendo la reserva actual.
        aulas = list(reserva.aulas.all())

        equipamientos_disponibles = obtener_equipamiento_disponible(
            fecha=reserva.fecha_reserva,
            hora_inicio=reserva.horario_inicio,
            hora_fin=reserva.horario_fin,
            aulas=aulas,
            excluir_reserva_id=reserva.pk,
        )

        disponibilidad = next(
            (
                item
                for item in equipamientos_disponibles
                if item["equipamiento"].pk == equipamiento.pk
            ),
            None,
        )

        cantidad_disponible = (
            disponibilidad["cantidad_disponible"]
            if disponibilidad is not None
            else 0
        )

        if cantidad_disponible <= 0:
            raise ValidationError(
                "No hay unidades disponibles de este equipamiento."
            )

        cantidad_reservada = min(
            cantidad_solicitada,
            cantidad_disponible,
        )

        # Si existe una solicitud automática para el nuevo
        # equipamiento, la reutilizamos y eliminamos la anterior.
        if otra_solicitud is not None:

            solicitud = otra_solicitud

            solicitud.cantidad_solicitada = cantidad_solicitada
            solicitud.cantidad_reservada = cantidad_reservada
            solicitud.cantidad_critica = cantidad_critica
            solicitud.asignacion_automatica = False

            solicitud.full_clean()
            solicitud.save()

            solicitud_actual.delete()

        else:

            # Si no existe otra solicitud, actualizamos la actual.
            solicitud = solicitud_actual

            solicitud.equipamiento = equipamiento
            solicitud.cantidad_solicitada = cantidad_solicitada
            solicitud.cantidad_reservada = cantidad_reservada
            solicitud.cantidad_critica = cantidad_critica
            solicitud.asignacion_automatica = False

            solicitud.full_clean()
            solicitud.save()

    return solicitud


def eliminar_solicitud_equipamiento(
    reserva_id,
    equipamiento_id,
):
    """
    Elimina una solicitud de equipamiento de una reserva.

    La operación se realiza dentro de una transacción
    para mantener la consistencia del stock.
    """

    with transaction.atomic():

        # 1. Bloqueamos la reserva.
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva indicada no existe."
            )

        # 2. Bloqueamos el equipamiento.
        try:
            equipamiento = Equipamiento.objects.select_for_update().get(
                pk=equipamiento_id
            )
        except Equipamiento.DoesNotExist:
            raise ValidationError(
                "El equipamiento indicado no existe."
            )

        # 3. Buscamos la solicitud.
        solicitud = SolicitudEquipo.objects.filter(
            reserva=reserva,
            equipamiento=equipamiento,
        ).first()

        if solicitud is None:
            raise ValidationError(
                "No existe una solicitud para ese equipamiento."
            )

        # 4. Eliminamos la solicitud.
        solicitud.delete()

    return True


def obtener_o_crear_participante(datos):
    """
    Busca un participante por tipo y número de documento.

    Si ya existe, lo devuelve sin duplicarlo.
    Si no existe, lo valida y lo crea.
    """

    datos = datos.copy()

    tipo_documento = datos.get("tipo_documento")
    numero_documento = datos.get("numero_documento")

    if not tipo_documento:
        raise ValidationError({
            "tipo_documento": "Debe indicar el tipo de documento."
        })

    if not numero_documento or not numero_documento.strip():
        raise ValidationError({
            "numero_documento": "Debe indicar un número de documento válido."
        })

    datos["numero_documento"] = numero_documento.strip()

    participante = Participante.objects.filter(
        tipo_documento=tipo_documento,
        numero_documento=datos["numero_documento"],
    ).first()

    if participante:
        return participante

    participante = Participante(**datos)
    participante.full_clean()

    try:
        with transaction.atomic():
            participante.save()
    except IntegrityError:
        participante = Participante.objects.get(
            tipo_documento=tipo_documento,
            numero_documento=datos["numero_documento"],
        )

    return participante



def asociar_participante_reserva(
    reserva_id,
    participante_id,
    rol="OTRO",
):
    """
    Asocia un participante a una reserva.

    Si ya está asociado, devuelve la asociación existente.
    Valida que el rol sea uno de los permitidos
    y que no se supere la capacidad total de las aulas.
    """

    roles_validos = dict(ReservaParticipante.ROL_CHOICES)

    if rol not in roles_validos:
        raise ValidationError({
            "rol": "El rol indicado no es válido."
        })

    with transaction.atomic():

        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError(
                "La reserva indicada no existe."
            )

        try:
            participante = Participante.objects.select_for_update().get(
                pk=participante_id
            )
        except Participante.DoesNotExist:
            raise ValidationError(
                "El participante indicado no existe."
            )

        # Si el participante ya está asociado, devolver la asociación.
        asociacion_existente = ReservaParticipante.objects.filter(
            reserva=reserva,
            participante=participante,
        ).first()

        if asociacion_existente:
            return asociacion_existente

        # Calcular la capacidad total de las aulas asociadas.
        capacidad_total = sum(
            reserva.aulas.values_list("capacidad", flat=True)
        )

        # Contar los participantes que ya tiene la reserva.
        cantidad_participantes = ReservaParticipante.objects.filter(
            reserva=reserva
        ).count()

        # Impedir que se supere la capacidad disponible.
        if cantidad_participantes >= capacidad_total:
            raise ValidationError({
                "participante": (
                    "No se puede agregar el participante porque "
                    "se alcanzó la capacidad total de las aulas "
                    "asociadas a la reserva."
                )
            })

        asociacion, creada = ReservaParticipante.objects.get_or_create(
            reserva=reserva,
            participante=participante,
            defaults={"rol": rol},
        )

    return asociacion


@transaction.atomic
def actualizar_rol_participante_reserva(
    reserva_id,
    participante_id,
    nuevo_rol,
):
    """
    Actualiza el rol de un participante dentro de una reserva.
    """

    roles_validos = dict(ReservaParticipante.ROL_CHOICES)

    if nuevo_rol not in roles_validos:
        raise ValidationError({
            "rol": "El rol indicado no es válido."
        })

    asociacion = ReservaParticipante.objects.select_for_update().filter(
        reserva_id=reserva_id,
        participante_id=participante_id,
    ).first()

    if not asociacion:
        raise ValidationError(
            "El participante no está asociado a esta reserva."
        )

    asociacion.rol = nuevo_rol
    asociacion.save(update_fields=["rol"])

    return asociacion


@transaction.atomic
def eliminar_participante_reserva(reserva_id, participante_id):
    """
    Quita la asociación de un participante con una reserva.
    No elimina el registro del participante.
    """

    asociacion = ReservaParticipante.objects.select_for_update().filter(
        reserva_id=reserva_id,
        participante_id=participante_id,
    ).first()

    if not asociacion:
        raise ValidationError(
            "El participante no está asociado a esta reserva."
        )

    asociacion.delete()


@transaction.atomic
def actualizar_asistencia_participante(
    reserva_id,
    participante_id,
    presente,
):
    """
    Registra o modifica la asistencia de un participante.

    Solo permite hacerlo si la reserva está confirmada
    o finalizada.

    presente:
        True  = asistió.
        False = no asistió.
        None  = asistencia sin registrar.
    """

    if presente not in (True, False, None):
        raise ValidationError({
            "presente": "El valor de asistencia no es válido."
        })

    try:
        reserva = Reserva.objects.select_for_update().get(
            pk=reserva_id
        )
    except Reserva.DoesNotExist:
        raise ValidationError(
            "La reserva indicada no existe."
        )

    estados_permitidos = [
        EstadoReserva.Estados.CONFIRMADA,
        EstadoReserva.Estados.FINALIZADA,
    ]

    if reserva.estado_reserva.estado not in estados_permitidos:
        raise ValidationError(
            "Solo se puede registrar la asistencia de reservas "
            "confirmadas o finalizadas."
        )

    asociacion = ReservaParticipante.objects.select_for_update().filter(
        reserva=reserva,
        participante_id=participante_id,
    ).first()

    if not asociacion:
        raise ValidationError(
            "El participante no está asociado a esta reserva."
        )

    asociacion.presente = presente
    asociacion.save(update_fields=["presente"])

    return asociacion


def _obtener_estado_reserva(estado):
    """Obtiene un estado de reserva o informa si no está configurado."""
    try:
        return EstadoReserva.objects.get(estado=estado)
    except EstadoReserva.DoesNotExist:
        raise ValidationError(
            f"El estado '{estado}' no está registrado en la base de datos."
        )


def _es_solicitante(reserva, usuario):
    return UsuarioPorReserva.objects.filter(
        reserva=reserva,
        usuario=usuario,
        solicitante=True,
    ).exists()


def _puede_operar_reserva(reserva, usuario):
    return (
        es_administrador(usuario)
        or _es_solicitante(reserva, usuario)
    )


def _obtener_fecha_hora_reserva(reserva, hora):
    fecha_hora = datetime.combine(reserva.fecha_reserva, hora)

    if timezone.is_aware(timezone.now()):
        fecha_hora = timezone.make_aware(
            fecha_hora,
            timezone.get_current_timezone(),
        )

    return fecha_hora


def _validar_recursos_reserva(reserva, exigir_aulas=True):
    """Comprueba que las aulas y el equipamiento sigan disponibles."""

    # Comprobamos que haya al menos un aula asignada,
    #si la operación lo requiere.
    aulas_ids = list(
        ReservaAula.objects.filter(
            reserva=reserva
        ).values_list("aula_id", flat=True)
    )

    if not aulas_ids and exigir_aulas:
        raise ValidationError(
            "No se puede confirmar una reserva sin aulas asignadas."
        )

    # Bloqueamos las aulas para evitar asignaciones concurrentes.
    aulas = list(
        Aula.objects.select_for_update()
        .filter(pk__in=sorted(aulas_ids))
        .order_by("pk")
    )

    if len(aulas) != len(aulas_ids):
        raise ValidationError(
            "Una o más aulas asignadas ya no existen."
        )

    if any(aula.estado != Aula.Estado.DISPONIBLE for aula in aulas):
        raise ValidationError(
            "Una o más aulas asignadas ya no están disponibles."
        )

    # Verificamos que no exista otra reserva que ocupe esas aulas.
    asignaciones_ocupadas = ReservaAula.objects.filter(
        aula_id__in=aulas_ids,
        reserva__fecha_reserva=reserva.fecha_reserva,
        reserva__estado_reserva__estado__in=ESTADOS_QUE_BLOQUEAN,
        reserva__horario_inicio__lt=reserva.horario_fin,
        reserva__horario_fin__gt=reserva.horario_inicio,
    ).exclude(
        reserva_id=reserva.pk
    )

    if asignaciones_ocupadas.exists():
        raise ValidationError(
            "Una o más aulas ya están ocupadas en ese día y horario."
        )

    # Recuperamos las solicitudes de equipamiento.
    solicitudes = list(
        SolicitudEquipo.objects.filter(
            reserva=reserva
        ).select_related("equipamiento").order_by("equipamiento_id")
    )

    if not solicitudes:
        return

    equipamiento_ids = sorted({
        solicitud.equipamiento_id
        for solicitud in solicitudes
    })

    # Bloqueamos el equipamiento para evitar compromisos simultáneos.
    equipos = list(
        Equipamiento.objects.select_for_update()
        .filter(pk__in=equipamiento_ids)
        .order_by("pk")
    )

    equipos_por_id = {
        equipo.pk: equipo
        for equipo in equipos
    }

    if len(equipos) != len(equipamiento_ids):
        raise ValidationError(
            "Uno o más equipos solicitados ya no existen."
        )

    equipos_expresos_ids = {
        solicitud.equipamiento_id
        for solicitud in solicitudes
        if not solicitud.asignacion_automatica
    }

    if any(
        equipo.estado != Equipamiento.Estado.DISPONIBLE
        for equipo in equipos
        if equipo.pk in equipos_expresos_ids
    ):
        raise ValidationError(
            "Uno o más equipos solicitados expresamente "
            "ya no están disponibles."
        )
    # Calculamos la disponibilidad excluyendo esta reserva,
    # porque sus solicitudes ya están comprometidas.
    disponibilidad = obtener_equipamiento_disponible(
        fecha=reserva.fecha_reserva,
        hora_inicio=reserva.horario_inicio,
        hora_fin=reserva.horario_fin,
        aulas=aulas,
        excluir_reserva_id=reserva.pk,
    )

    disponibilidad_por_id = {
        item["equipamiento"].pk: item["cantidad_disponible"]
        for item in disponibilidad
    }

    for solicitud in solicitudes:
        equipo = equipos_por_id[solicitud.equipamiento_id]

        # Si es una asignación automática y el equipo dejó de estar
        # disponible, no debe impedir la confirmación de la reserva.
        if (
            solicitud.asignacion_automatica
            and equipo.estado != Equipamiento.Estado.DISPONIBLE
        ):
            continue

        cantidad = (
            solicitud.cantidad_reservada
            if solicitud.cantidad_reservada is not None
            else solicitud.cantidad_solicitada
        )

        if cantidad < 1 or cantidad > solicitud.cantidad_solicitada:
            raise ValidationError(
                f"La cantidad reservada de '{equipo.nombre}' no es válida."
            )

        cantidad_disponible = disponibilidad_por_id.get(equipo.pk, 0)

        if cantidad > equipo.cantidad:
            raise ValidationError(
                f"La cantidad solicitada de '{equipo.nombre}' "
                "supera el stock total."
            )

        if cantidad > cantidad_disponible:
            raise ValidationError(
                f"Stock insuficiente de '{equipo.nombre}'. "
                f"Cantidad disponible: {cantidad_disponible}."
            )


def confirmar_reserva(reserva_id, usuario):
    """Confirma una reserva pendiente luego de validar sus recursos."""

    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError("La reserva indicada no existe.")

        if not es_administrador(usuario):
            raise ValidationError(
                "Solamente Administración puede confirmar esta reservas."
            )

        if (
            reserva.estado_reserva is None
            or reserva.estado_reserva.estado
            != EstadoReserva.Estados.PENDIENTE
        ):
            raise ValidationError(
                "Solamente se pueden confirmar reservas pendientes."
            )

        validar_solicitante_reserva(reserva)

        _validar_recursos_reserva(reserva)

        reserva.estado_reserva = _obtener_estado_reserva(
            EstadoReserva.Estados.CONFIRMADA
        )
        reserva.save(update_fields=["estado_reserva"])

    return reserva


def rechazar_reserva(reserva_id, usuario):
    """Rechaza una reserva pendiente."""

    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError("La reserva indicada no existe.")

        if not es_administrador(usuario):
            raise ValidationError(
                "Solamente Administración puede rechazar reservas."
            )

        if (
            reserva.estado_reserva is None
            or reserva.estado_reserva.estado
            != EstadoReserva.Estados.PENDIENTE
        ):
            raise ValidationError(
                "Solamente se pueden rechazar reservas pendientes."
            )

        reserva.estado_reserva = _obtener_estado_reserva(
            EstadoReserva.Estados.RECHAZADA
        )
        reserva.save(update_fields=["estado_reserva"])

    return reserva


def cancelar_reserva(reserva_id, usuario):
    """Cancela una reserva según el usuario y el horario reservado."""

    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_for_update().get(
                pk=reserva_id
            )
        except Reserva.DoesNotExist:
            raise ValidationError("La reserva indicada no existe.")

        if not _puede_operar_reserva(reserva, usuario):
            raise ValidationError(
                "No tenés permisos para cancelar esta reserva."
            )

        if reserva.estado_reserva is None:
            raise ValidationError(
                "La reserva no tiene un estado asignado."
            )

        estado_actual = reserva.estado_reserva.estado

        if estado_actual == EstadoReserva.Estados.PENDIENTE:
            pass

        elif estado_actual == EstadoReserva.Estados.CONFIRMADA:
            inicio = _obtener_fecha_hora_reserva(
                reserva,
                reserva.horario_inicio,
            )

            if timezone.now() >= inicio:
                raise ValidationError(
                    "Una reserva confirmada solamente puede cancelarse "
                    "antes de su horario de inicio."
                )

        else:
            raise ValidationError(
                "Esta reserva no se puede cancelar porque su estado "
                "ya es definitivo."
            )

        reserva.estado_reserva = _obtener_estado_reserva(
            EstadoReserva.Estados.CANCELADA
        )
        reserva.save(update_fields=["estado_reserva"])

    return reserva


def finalizar_reservas_vencidas():
    """
    Cancela reservas pendientes que llegaron a su horario de inicio
    y finaliza reservas confirmadas cuyo horario de fin ya pasó.

    Devuelve un diccionario con la cantidad de reservas canceladas
    y finalizadas.
    """
    ahora = timezone.now()
    reservas_canceladas = 0
    reservas_finalizadas = 0

    reservas = Reserva.objects.filter(
        estado_reserva__estado__in=[
            EstadoReserva.Estados.PENDIENTE,
            EstadoReserva.Estados.CONFIRMADA,
        ]
    ).order_by("pk")

    for reserva_id in reservas.values_list("pk", flat=True):
        with transaction.atomic():
            try:
                reserva = Reserva.objects.select_for_update().get(
                    pk=reserva_id
                )
            except Reserva.DoesNotExist:
                continue

            if reserva.estado_reserva is None:
                continue

            estado_actual = reserva.estado_reserva.estado

            if estado_actual == EstadoReserva.Estados.PENDIENTE:
                momento_limite = _obtener_fecha_hora_reserva(
                    reserva,
                    reserva.horario_inicio,
                )

                if momento_limite <= ahora:
                    reserva.estado_reserva = _obtener_estado_reserva(
                        EstadoReserva.Estados.CANCELADA
                    )
                    reserva.save(update_fields=["estado_reserva"])
                    reservas_canceladas += 1

            elif estado_actual == EstadoReserva.Estados.CONFIRMADA:
                momento_limite = _obtener_fecha_hora_reserva(
                    reserva,
                    reserva.horario_fin,
                )

                if momento_limite <= ahora:
                    reserva.estado_reserva = _obtener_estado_reserva(
                        EstadoReserva.Estados.FINALIZADA
                    )
                    reserva.save(update_fields=["estado_reserva"])
                    reservas_finalizadas += 1

    return {
        "canceladas": reservas_canceladas,
        "finalizadas": reservas_finalizadas,
    }


def actualizar_estados_reservas():
    """
    Actualiza los estados de las reservas vencidas.
    """
    return finalizar_reservas_vencidas()
