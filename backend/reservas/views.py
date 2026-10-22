from datetime import date, time

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services import obtener_aulas_disponibles


@api_view(["GET"])
def aulas_disponibles(request):
    fecha_texto = request.query_params.get("fecha")
    hora_inicio_texto = request.query_params.get("hora_inicio")
    hora_fin_texto = request.query_params.get("hora_fin")

    if not fecha_texto or not hora_inicio_texto or not hora_fin_texto:
        return Response(
            {
                "error": "Debés indicar fecha, hora_inicio y hora_fin."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        fecha = date.fromisoformat(fecha_texto)
        hora_inicio = time.fromisoformat(hora_inicio_texto)
        hora_fin = time.fromisoformat(hora_fin_texto)
    except ValueError:
        return Response(
            {
                "error": "Formato inválido. Usá fecha AAAA-MM-DD y horas HH:MM."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if hora_inicio >= hora_fin:
        return Response(
            {
                "error": "La hora de fin debe ser posterior a la hora de inicio."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    aulas = obtener_aulas_disponibles(
        fecha,
        hora_inicio,
        hora_fin,
    )

    resultado = [
        {
            "id": aula.pk,
            "nombre": aula.nombre,
            "capacidad": aula.capacidad,
        }
        for aula in aulas
    ]

    return Response(resultado)
