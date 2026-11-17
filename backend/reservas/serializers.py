from rest_framework import serializers

from .models import (
    Actividad,
    EstadoReserva,
    Reserva,
    Participante,
    ReservaParticipante,
    SolicitudEquipo,
    UsuarioPorReserva,
)


class ConsultaDisponibilidadSerializer(serializers.Serializer):
    fecha = serializers.DateField(input_formats=["%Y-%m-%d"])
    hora_inicio = serializers.TimeField(
        input_formats=["%H:%M", "%H:%M:%S"]
    )
    hora_fin = serializers.TimeField(
        input_formats=["%H:%M", "%H:%M:%S"]
    )
    capacidad_min = serializers.IntegerField(
        min_value=1,
        required=False
    )

    def validate(self, attrs):
        if attrs["hora_inicio"] >= attrs["hora_fin"]:
            raise serializers.ValidationError({
                "hora_fin": (
                    "La hora de fin debe ser posterior "
                    "a la hora de inicio."
                )
            })
        return attrs


class ActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actividad
        fields = "__all__"
        read_only_fields = [
            "id_actividad",
            "responsable",
        ]


class ReservaSerializer(serializers.ModelSerializer):
    actividad_nombre = serializers.CharField(
        source="actividad.nombre",
        read_only=True
    )
    estado = serializers.CharField(
        source="estado_reserva.estado",
        read_only=True
    )
    aulas = serializers.SerializerMethodField()

    def get_aulas(self, obj):
        return [
            {
                "id": aula.pk,
                "nombre": aula.nombre,
                "capacidad": aula.capacidad,
            }
            for aula in obj.aulas.all()
        ]

    class Meta:
        model = Reserva
        fields = [
            "id_reserva",
            "actividad",
            "actividad_nombre",
            "fecha_reserva",
            "horario_inicio",
            "horario_fin",
            "detalle",
            "estado_reserva",
            "estado",
            "cod_reunion",
            "aulas",
        ]
        read_only_fields = [
            "id_reserva",
            "estado_reserva",
            "estado",
            "aulas",
        ]


class ParticipanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participante
        fields = "__all__"
        read_only_fields = [
            "id_participante",
            "creado_por",
        ]


class ReservaParticipanteSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReservaParticipante
        fields = "__all__"
        read_only_fields = ["id_reserva_participante"]


class SolicitudEquipoSerializer(serializers.ModelSerializer):

    cantidad_critica_alcanzada = serializers.SerializerMethodField()

    def get_cantidad_critica_alcanzada(self, obj):
        if obj.cantidad_reservada is None:
            return False

        return obj.cantidad_reservada >= obj.cantidad_critica

    class Meta:
        model = SolicitudEquipo
        fields = "__all__"
        read_only_fields = [
            "id_solicitud_por_equipo",
            "cantidad_reservada",
            "asignacion_automatica",
        ]

    def validate(self, attrs):
        # Impedir que se cambie la reserva de una solicitud existente.
        if (
            self.instance
            and "reserva" in attrs
            and attrs["reserva"].pk != self.instance.reserva_id
        ):
            raise serializers.ValidationError({
                "reserva": (
                    "No se puede cambiar la reserva asociada "
                    "a una solicitud de equipamiento."
                )
            })

        cantidad_solicitada = attrs.get(
            "cantidad_solicitada",
            getattr(self.instance, "cantidad_solicitada", None),
        )

        cantidad_reservada = attrs.get(
            "cantidad_reservada",
            getattr(self.instance, "cantidad_reservada", None),
        )

        cantidad_critica = attrs.get(
            "cantidad_critica",
            getattr(self.instance, "cantidad_critica", None),
        )

        if cantidad_reservada is not None and cantidad_reservada < 0:
            raise serializers.ValidationError({
                "cantidad_reservada":
                    "La cantidad reservada no puede ser negativa."
            })

        if cantidad_critica is not None and cantidad_critica < 0:
            raise serializers.ValidationError({
                "cantidad_critica":
                    "La cantidad crítica no puede ser negativa."
            })

        if cantidad_solicitada is not None and cantidad_solicitada < 1:
            raise serializers.ValidationError({
                "cantidad_solicitada":
                    "La cantidad solicitada debe ser mayor que cero."
            })

        if (
            cantidad_critica is not None
            and cantidad_solicitada is not None
            and cantidad_critica > cantidad_solicitada
        ):
            raise serializers.ValidationError({
                "cantidad_critica":
                    "La cantidad crítica no puede superar la cantidad solicitada."
            })

        if (
            cantidad_reservada is not None
            and cantidad_solicitada is not None
            and cantidad_reservada > cantidad_solicitada
        ):
            raise serializers.ValidationError({
                "cantidad_reservada":
                    "La cantidad reservada no puede superar la cantidad solicitada."
            })

        return attrs


class EstadoReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoReserva
        fields = ['id_estado_reserva', 'estado']
        read_only_fields = ["id_estado_reserva"]


class UsuarioPorReservaSerializer(serializers.ModelSerializer):
    # Opcional: si querés mostrar detalles del usuario o la reserva en la lectura,
    # podés descomentar o ajustar estos campos de solo lectura.
    # usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    # reserva_id = serializers.PrimaryKeyRelatedField(source="reserva", read_only=True)

    class Meta:
        model = UsuarioPorReserva
        fields = [
            "id_usuario_por_reserva",
            "reserva",
            "usuario",
            "solicitante",
        ]
        read_only_fields = ["id_usuario_por_reserva"]
        validators = []
