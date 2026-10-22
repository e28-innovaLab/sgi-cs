from django.db import models
from django.core.validators import MinValueValidator


class Aula(models.Model):
    class Tipo(models.TextChoices):
        AULA = 'AULA', 'Aula'
        LABORATORIO = 'LABORATORIO', 'Laboratorio'
        TALLER = 'TALLER', 'Taller'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        MANTENIMIENTO = 'MANTENIMIENTO', 'En mantenimiento'
        FUERA_SERVICIO = 'FUERA_SERVICIO', 'Fuera de servicio'

    id_aula = models.AutoField(
        primary_key=True,
        db_column="idAula",
    )

    nombre = models.CharField(
        max_length=100,
        unique=True,
    )

    capacidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AULA)
    ubicacion = models.CharField(max_length=200, blank=True, default='')
    caracteristicas = models.TextField(blank=True, default='')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)

    sillas = models.PositiveIntegerField(default=0)

    mesas = models.PositiveIntegerField(default=0)

    color = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = "aula"
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"


class Categoria(models.Model):
    id_categoria = models.AutoField(
        primary_key=True,
        db_column="idCategoria",
    )

    nombre = models.CharField(
        max_length=100,
        unique=True,
        db_column="categoria",
    )

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = "categoria"
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"


class Equipamiento(models.Model):

    class Estado(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        MANTENIMIENTO = "MANTENIMIENTO", "En mantenimiento"
        FUERA_SERVICIO = "FUERA_SERVICIO", "Fuera de servicio"

    id_equipo = models.AutoField(
        primary_key=True,
        db_column="idEquipo",
    )

    nombre = models.CharField(
        max_length=150,
        db_column="nombreEquipamiento",
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="equipamientos",
        db_column="idCategoria",
    )

    aula = models.ForeignKey(
        Aula,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipamientos",
        db_column="idAula",
    )

    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.DISPONIBLE,
        null=True,
        blank=True,
    )

    trasladable = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = "equipamiento"
        verbose_name = "Equipamiento"
        verbose_name_plural = "Equipamientos"

