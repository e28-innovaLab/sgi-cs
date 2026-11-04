from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import obtener_aulas_disponibles
from .serializers import ConsultaDisponibilidadSerializer


@api_view(["GET"])
def aulas_disponibles(request):
    consulta = ConsultaDisponibilidadSerializer(data=request.query_params)
    consulta.is_valid(raise_exception=True)
    datos = consulta.validated_data

    aulas = obtener_aulas_disponibles(
        datos['fecha'],
        datos['hora_inicio'],
        datos['hora_fin'],
    )
    if 'capacidad_min' in datos:
        aulas = aulas.filter(capacidad__gte=datos['capacidad_min'])

    resultado = [
        {
            "id": aula.pk,
            "nombre": aula.nombre,
            "capacidad": aula.capacidad,
        }
        for aula in aulas
    ]

    return Response(resultado)
