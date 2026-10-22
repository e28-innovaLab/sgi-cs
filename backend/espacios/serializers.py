from rest_framework import serializers

from .models import Aula, Categoria, Equipamiento


class AulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aula
        fields = [
            'id_aula', 'nombre', 'tipo', 'ubicacion', 'caracteristicas',
            'estado', 'capacidad', 'sillas', 'mesas', 'color',
        ]
        read_only_fields = ['id_aula']


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']
        read_only_fields = ['id_categoria']


class EquipamientoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    aula_nombre = serializers.CharField(source='aula.nombre', read_only=True, allow_null=True)
    estado = serializers.ChoiceField(choices=Equipamiento.Estado.choices, required=False)

    class Meta:
        model = Equipamiento
        fields = [
            'id_equipo', 'nombre', 'categoria', 'categoria_nombre', 'aula',
            'aula_nombre', 'cantidad', 'estado', 'trasladable',
        ]
        read_only_fields = ['id_equipo']

    def validate(self, attrs):
        trasladable = attrs.get('trasladable', getattr(self.instance, 'trasladable', False))
        aula = attrs.get('aula', getattr(self.instance, 'aula', None))
        if not trasladable and aula is None:
            raise serializers.ValidationError({'aula': 'El equipamiento fijo debe tener un aula asignada.'})
        return attrs


class EstadoAulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aula
        fields = ['estado']
        extra_kwargs = {'estado': {'required': True}}


class EstadoEquipamientoSerializer(serializers.ModelSerializer):
    estado = serializers.ChoiceField(choices=Equipamiento.Estado.choices)

    class Meta:
        model = Equipamiento
        fields = ['estado']


class FiltrosAulaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=Aula.Tipo.choices, required=False)
    estado = serializers.ChoiceField(choices=Aula.Estado.choices, required=False)
    capacidad_min = serializers.IntegerField(min_value=1, required=False)


class FiltrosEquipamientoSerializer(serializers.Serializer):
    aula = serializers.IntegerField(min_value=1, required=False)
    categoria = serializers.IntegerField(min_value=1, required=False)
    estado = serializers.ChoiceField(choices=Equipamiento.Estado.choices, required=False)
    trasladable = serializers.BooleanField(required=False)
