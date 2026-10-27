from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from .opciones import NACIONALIDADES


class EstadoReserva(models.Model):

    class Estados(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        CONFIRMADA = "Confirmada", "Confirmada"
        CANCELADA = "Cancelada", "Cancelada"
        RECHAZADA = "Rechazada", "Rechazada"

    id_estado_reserva = models.AutoField(
        primary_key=True,
        db_column="idEstadoReserva",
    )

    estado = models.CharField(
        max_length=50,
        choices=Estados.choices,
        unique=True,
    )

    class Meta:
        db_table = "estadoReserva"
        verbose_name = "Estado de reserva"
        verbose_name_plural = "Estados de reserva"
        ordering = ["id_estado_reserva"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    estado__in=[
                        "Pendiente",
                        "Confirmada",
                        "Cancelada",
                        "Rechazada",
                    ]
                ),
                name="estado_reserva_valido",
            )
        ]

    def __str__(self):
        return self.estado


class Actividad(models.Model):

    class Tipo(models.TextChoices):
        CURSO = "CURSO", "Curso"
        PRACTICA = "PRACTICA", "Práctica"
        WORKSHOP = "WORKSHOP", "Workshop"
        CAPACITACION = "CAPACITACION", "Capacitación"
        OTRA = "OTRA", "Otra"

    id_actividad = models.AutoField(
        primary_key=True,
        db_column="idActividad",
    )

    nombre = models.CharField(
        max_length=200,
        db_column="nombreActividad",
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        db_column="tipoActividad",
    )

    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="actividades_responsable",
        db_column="idResponsable",
    )

    fecha_estimada = models.DateField(
        db_column="fechaEstimada",
    )

    horario_inicio_estimado = models.TimeField(
        db_column="horarioInicioEstimado",
    )

    horario_fin_estimado = models.TimeField(
        db_column="horarioFinEstimado",
    )

    participantes_estimados = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        db_column="participantesEstimados",
    )

    requerimiento_espacio = models.TextField(
        blank=True,
        default="",
        db_column="requerimientoEspacio",
    )

    equipamiento_necesario = models.TextField(
        blank=True,
        default="",
        db_column="equipamientoNecesario",
    )

    class Meta:
        db_table = "actividad"
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ["fecha_estimada", "horario_inicio_estimado"]

    def clean(self):
        super().clean()
        if (
            self.horario_inicio_estimado is not None
            and self.horario_fin_estimado is not None
            and self.horario_inicio_estimado >= self.horario_fin_estimado
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError({
                "horario_fin_estimado":
                    "La hora de fin debe ser posterior a la hora de inicio."
            })

    def __str__(self):
        return self.nombre


class Reserva(models.Model):

    id_reserva = models.AutoField(
        primary_key=True,
        db_column="idReserva",
    )

    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.PROTECT,
        related_name="reservas",
        db_column="idActividad",
    )

    usuarios = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="UsuarioPorReserva",
        related_name="reservas",
    )

    participantes = models.ManyToManyField(
    "Participante",
    through="ReservaParticipante",
    related_name="reservas",
    blank=True,
    )

    fecha_reserva = models.DateField(
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
        return f"{self.actividad.nombre} - {self.fecha_reserva}"


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

    TIPO_DOCUMENTO_CHOICES = [
        ("DNI", "DNI"),
        ("LE", "Libreta de Enrolamiento (LE)"),
        ("LC", "Libreta Cívica (LC)"),
        ("CI", "Cédula de Identidad (CI)"),
        ("PASAPORTE", "Pasaporte"),
        ("OTRO", "Otro"),
    ]

    GENERO_CHOICES = [
        ("FEMENINO", "Femenino"),
        ("MASCULINO", "Masculino"),
        ("OTRO", "Otro"),
    ]

    LUGAR_RESIDENCIA_CHOICES = [
        ("CABA", "Ciudad Autónoma de Buenos Aires"),
        ("PROVINCIA_BA", "Provincia de Buenos Aires"),
    ]

    id_participante = models.AutoField(
        primary_key=True,
        db_column="idParticipante",
    )

    nombres = models.CharField(max_length=100)

    apellidos = models.CharField(max_length=100)

    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES,
        db_column="tipoDoc",
    )

    # Texto para admitir documentos nacionales y extranjeros.
    numero_documento = models.CharField(
        max_length=30,
        db_column="numeroDoc",
    )

    fecha_nacimiento = models.DateField(
        db_column="fechaNacimiento",
    )

    genero = models.CharField(
        max_length=20,
        choices=GENERO_CHOICES,
        null=True,
        blank=True,
    )

    nacionalidad = models.CharField(
        max_length=100,
        choices=NACIONALIDADES,                                                               
    )

    domicilio = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    lugar_residencia = models.CharField(
        max_length=20,
        choices=LUGAR_RESIDENCIA_CHOICES,
        db_column="lugarResidencia",
    )

    mail = models.EmailField()

    celular = models.CharField(max_length=30)

    institucion = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "participante"

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class ReservaParticipante(models.Model):
    id_reserva_participante = models.AutoField(
        primary_key=True,
        db_column="idReservaParticipante",
    )

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="reservas_participantes",
        db_column="idReserva",
    )

    participante = models.ForeignKey(
        Participante,
        on_delete=models.CASCADE,
        related_name="reservas_participantes",
        db_column="idParticipante",
    )

    presente = models.BooleanField(
        null=True,
        blank=True,
    )

    ROL_CHOICES = [
    ("DOCENTE", "Docente"),
    ("AYUDANTE_DOCENTE", "Ayudante docente"),
    ("ESTUDIANTE", "Estudiante"),
    ("OBSERVADOR", "Observador"),
    ("VISITA", "Visita"),
    ("OTRO", "Otro"),
    ]

    rol = models.CharField(
    max_length=20,
    choices=ROL_CHOICES,
    default="OTRO",
    )

    class Meta:
        db_table = "reservaParticipante"
        constraints = [
            models.UniqueConstraint(
                fields=["reserva", "participante"],
                name="reserva_participante_unico",
            ),
        ]

    def __str__(self):
        return f"{self.reserva} - {self.participante}"