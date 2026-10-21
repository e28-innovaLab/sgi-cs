
from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    id_rol = models.AutoField(
        primary_key=True,
        db_column="idRol",
    )

    nombre = models.CharField(
        max_length=20,
        unique=True,
        db_column="rol",
    )

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = "rol"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"


class Usuario(AbstractUser):
    id_usuario = models.AutoField(
        primary_key=True,
        db_column="idUsuario",
    )

    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        related_name="usuarios",
        db_column="idRol",
    )

    # Datos personales.
    first_name = models.CharField(
        "Nombres",
        max_length=150,
        db_column="nombres",
    )

    last_name = models.CharField(
        "Apellidos",
        max_length=150,
        db_column="apellidos",
    )

    tipo_documento = models.CharField(
        max_length=20,
        db_column="tipoDoc",
    )

    numero_documento = models.CharField(
        max_length=30,
        unique=True,
        db_column="numeroDoc",
    )

    email = models.EmailField(
        "Correo electrónico",
        db_column="mail",
    )

    # Fechas de creación e ingreso.
    date_joined = models.DateTimeField(
        "Creación de usuario",
        auto_now_add=True,
        db_column="creacionUsuario",
    )

    last_login = models.DateTimeField(
        "Último ingreso",
        null=True,
        blank=True,
        db_column="ultimoIngreso",
    )

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
