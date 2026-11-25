from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import EsEquipoDelCentro
from .parser import interpretar_pregunta, PreguntaNoReconocida
from .services import resolver_consulta


EJEMPLOS = [
    '¿Qué laboratorios están disponibles mañana de 14 a 16 para 20 personas?',
    '¿Cuántas reservas hubo este mes?',
    '¿Qué espacios tuvieron mayor ocupación este mes?',
    '¿Qué equipos tuvieron mayor utilización el mes pasado?',
    '¿Qué actividades tienen equipamiento pendiente mañana?',
]


class PreguntaSerializer(serializers.Serializer):
    pregunta = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)
    limite = serializers.IntegerField(min_value=1, max_value=20, default=5)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            desconocidos = set(data) - set(self.fields)
            if desconocidos:
                raise serializers.ValidationError({k: 'Campo no admitido.' for k in sorted(desconocidos)})
        return super().to_internal_value(data)


class ConsultaInteligenteView(APIView):
    # Propio del módulo: no depende de cambios en el permiso global de la API.
    permission_classes = [EsEquipoDelCentro]

    def get(self, request):
        return Response({
            'motor': 'local_reglas',
            'descripcion': 'Consultas sencillas en español sobre datos reales. No usa un modelo de lenguaje.',
            'capacidades': ['disponibilidad_aulas', 'resumen_reservas', 'utilizacion_espacios',
                            'utilizacion_equipos', 'alertas_operativas'],
            'ejemplos': EJEMPLOS,
        })

    def post(self, request):
        serializer = PreguntaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pregunta = serializer.validated_data['pregunta']
        try:
            plan = interpretar_pregunta(pregunta)
            respuesta, datos, fuentes = resolver_consulta(plan, serializer.validated_data['limite'])
        except PreguntaNoReconocida as exc:
            return Response({
                'codigo': 'consulta_no_reconocida', 'necesita_aclaracion': True,
                'respuesta': str(exc), 'ejemplos': EJEMPLOS,
            }, status=400)
        return Response({
            'motor': 'local_reglas', 'pregunta': pregunta, 'interpretacion': plan,
            'respuesta': respuesta, 'datos': datos, 'fuentes': fuentes,
        })
