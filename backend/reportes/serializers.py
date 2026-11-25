from datetime import time, timedelta

from django.utils import timezone
from rest_framework import serializers

from reservas.models import Actividad, EstadoReserva
from .models import HistorialReserva


class ConsultaReporteSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    aula = serializers.IntegerField(min_value=1, required=False)
    equipamiento = serializers.IntegerField(min_value=1, required=False)
    tipo_actividad = serializers.ChoiceField(choices=Actividad.Tipo.choices, required=False)
    estado = serializers.ChoiceField(
        choices=[*EstadoReserva.Estados.values, 'SIN_ESTADO'], required=False,
    )
    hora_apertura = serializers.TimeField(default=time(8), input_formats=['%H:%M', '%H:%M:%S'])
    hora_cierre = serializers.TimeField(default=time(20), input_formats=['%H:%M', '%H:%M:%S'])
    reserva = serializers.IntegerField(min_value=1, required=False)
    nivel = serializers.ChoiceField(choices=['ADVERTENCIA', 'CRITICA'], required=False)

    def to_internal_value(self, data):
        desconocidos = set(data) - set(self.fields) - {'page'}
        if desconocidos:
            raise serializers.ValidationError({campo: 'Filtro desconocido.' for campo in sorted(desconocidos)})
        return super().to_internal_value(data)

    def validate(self, attrs):
        hoy = timezone.localdate()
        if self.context.get('alertas'):
            attrs.setdefault('desde', hoy)
            attrs.setdefault('hasta', attrs['desde'] + timedelta(days=29))
        else:
            attrs.setdefault('hasta', attrs.get('desde', hoy) + (
                timedelta(days=29) if 'desde' in attrs else timedelta()
            ))
            attrs.setdefault('desde', attrs['hasta'] - timedelta(days=29))
        if attrs['desde'] > attrs['hasta']:
            raise serializers.ValidationError({'hasta': 'Debe ser igual o posterior a desde.'})
        if (attrs['hasta'] - attrs['desde']).days >= 366:
            raise serializers.ValidationError({'hasta': 'El período máximo es de 366 días inclusivos.'})
        if attrs['hora_apertura'] >= attrs['hora_cierre']:
            raise serializers.ValidationError({'hora_cierre': 'Debe ser posterior a hora_apertura.'})
        return attrs


class HistorialReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialReserva
        fields = ['id', 'reserva_original_id', 'fecha_reserva', 'registrado_en', 'evento', 'datos']
        read_only_fields = fields
