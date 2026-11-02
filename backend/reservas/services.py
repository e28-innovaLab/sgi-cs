from django.core.exceptions import ValidationError

from espacios.models import Aula, Equipamiento
from .models import (
    ReservaAula,
    SolicitudEquipo,
    EstadoReserva,
    UsuarioPorReserva,
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
        raise ValueError(
            "La hora de fin debe ser posterior a la hora de inicio."
        )

    aula_ids = [
        aula.pk if isinstance(aula, Aula) else aula
        for aula in aulas
    ]

    if not aula_ids:
        raise ValueError(
            "Debe indicar al menos un aula para consultar equipamiento."
        )

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