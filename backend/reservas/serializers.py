from rest_framework import serializers


class ConsultaDisponibilidadSerializer(serializers.Serializer):
    fecha = serializers.DateField(input_formats=['%Y-%m-%d'])
    hora_inicio = serializers.TimeField(input_formats=['%H:%M', '%H:%M:%S'])
    hora_fin = serializers.TimeField(input_formats=['%H:%M', '%H:%M:%S'])
    capacidad_min = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        if attrs['hora_inicio'] >= attrs['hora_fin']:
            raise serializers.ValidationError({'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'})
        return attrs
