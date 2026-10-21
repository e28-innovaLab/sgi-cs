from django.conf import settings
from django.db import models


class EstadoReserva(models.Model):
    id_estado_reserva = models.AutoField(
        primary_key=True,
        db_column="idEstadoReserva",
    )

    estado = models.CharField(max_length=50)

    class Meta:
        db_table = "estadoReserva"
        verbose_name = "Estado de reserva"
        verbose_name_plural = "Estados de reserva"

    def __str__(self):
        return self.estado


class Reserva(models.Model):
    id_reserva = models.AutoField(
        primary_key=True,
        db_column="idReserva",
    )

    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="UsuarioPorReserva",
        related_name="reservas",
    )

    nombre_actividad = models.CharField(
        max_length=200,
        db_column="nombreActividad",
    )

    tipo_actividad = models.CharField(
        max_length=100,
        db_column="tipoActividad",
    )

    fecha_reserva = models.DateTimeField(
        db_column="fechaReserva",
    )

    horario_inicio = models.TimeField(
        db_column="horarioInicio",
    )

    horario_fin = models.TimeField(
        db_column="horarioFin",
    )

    detalle = models.TextField(
        null=True,
        blank=True,
        db_column="detalle",
    )

    estado_reserva = models.ForeignKey(
        EstadoReserva,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservas",
        db_column="idEstadoReserva",
    )

    cod_reunion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column="codReunion",
    )

    aulas = models.ManyToManyField(
        "espacios.Aula",
        through="ReservaAula",
        related_name="reservas",
    )

    class Meta:
        db_table = "reserva"

    def __str__(self):
        return self.nombre_actividad


class UsuarioPorReserva(models.Model):
    id_usuario_por_reserva = models.AutoField(
        primary_key=True,
        db_column="idUsuarioPorReserva",
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="usuarios_asociados",
        db_column="idReserva",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas_asociadas",
        db_column="idUsuario",
    )

    solicitante = models.BooleanField(default=False)

    class Meta:
        db_table = "usuarioPorReserva"
        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "usuario"],
                name="usuario_reserva_unico",
            )
        ]

    def __str__(self):
        return f"{self.usuario} - {self.reserva}"


class ReservaAula(models.Model):
    id_reserva_por_aula = models.AutoField(
        primary_key=True,
        db_column="idReservaPorAula",
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        db_column="idReserva",
    )

    aula = models.ForeignKey(
        "espacios.Aula",
        on_delete=models.PROTECT,
        db_column="idAula",
    )

    estado_reserva = models.BooleanField(
        null=True,
        blank=True,
        db_column="estadoReserva",
    )

    class Meta:
        db_table = "reservaPorAula"
        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "aula"],
                name="reserva_aula_unica",
            )
        ]

    def __str__(self):
        return f"{self.reserva} - {self.aula}"


class SolicitudEquipo(models.Model):
    id_solicitud_por_equipo = models.AutoField(
        primary_key=True,
        db_column="idSolicitudPorEquipo",
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="solicitudes_equipo",
        db_column="idReserva",
    )

    equipamiento = models.ForeignKey(
        "espacios.Equipamiento",
        on_delete=models.PROTECT,
        related_name="solicitudes_reserva",
        db_column="idEquipo",
    )

    cantidad_solicitada = models.PositiveIntegerField(
        db_column="cantidadSolicitada",
    )

    cantidad_reservada = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_column="cantidadReservada",
    )

    cantidad_critica = models.PositiveIntegerField(
        db_column="cantidadCritica",
    )

    estado_reserva = models.BooleanField(
        null=True,
        blank=True,
        db_column="estadoReserva",
    )

    class Meta:
        db_table = "solicitudPorEquipo"

    def __str__(self):
        return f"{self.reserva} - {self.equipamiento}"


class Participante(models.Model):
    id_participante = models.AutoField(
        primary_key=True,
        db_column="idParticipante",
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="participantes",
        db_column="idReserva",
    )

    nombres = models.CharField(max_length=100)

    apellidos = models.CharField(max_length=100)

    tipo_documento = models.CharField(
        max_length=20,
        db_column="tipoDoc",
    )

    numero_documento = models.CharField(
        max_length=30,
        db_column="numeroDoc",
    )

    fecha_nacimiento = models.DateField(
        db_column="fechaNacimiento",
    )

    genero = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    nacionalidad = models.CharField(max_length=100)

    domicilio = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    lugar_residencia = models.CharField(
        max_length=150,
        db_column="lugarResidencia",
    )

    mail = models.EmailField()

    celular = models.CharField(max_length=30)

    institucion = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    presente = models.BooleanField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "participante"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
