from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion



def copiar_reserva_a_actividad(apps, schema_editor):
    Reserva = apps.get_model("reservas", "Reserva")
    Actividad = apps.get_model("reservas", "Actividad")
    Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    reservas = list(Reserva.objects.all())

    # Si no hay reservas antiguas, no hay nada que migrar.
    if not reservas:
        return

    # Primero intentamos encontrar al usuario abel.
    responsable = Usuario.objects.filter(
        username="abel",
        is_active=True,
    ).first()

    # Si no existe, utilizamos otro usuario activo.
    if responsable is None:
        responsable = Usuario.objects.filter(
            is_active=True,
        ).order_by("pk").first()

    if responsable is None:
        raise RuntimeError(
            "No hay usuarios activos para asignar como responsables "
            "de las actividades existentes."
        )

    for reserva in reservas:
        actividad = Actividad.objects.create(
            nombre=reserva.nombre_actividad,
            tipo="OTRA",
            responsable_id=responsable.pk,
            fecha_estimada=reserva.fecha_reserva,
            horario_inicio_estimado=reserva.horario_inicio,
            horario_fin_estimado=reserva.horario_fin,
            participantes_estimados=1,
            requerimiento_espacio="",
            equipamiento_necesario="",
        )

        reserva.actividad_id = actividad.pk
        reserva.save(update_fields=["actividad"])


class Migration(migrations.Migration):

    dependencies = [
        ("reservas", "0004_alter_estadoreserva_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Actividad",
            fields=[
                (
                    "id_actividad",
                    models.AutoField(
                        db_column="idActividad",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        db_column="nombreActividad",
                        max_length=200,
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("CURSO", "Curso"),
                            ("PRACTICA", "Práctica"),
                            ("WORKSHOP", "Workshop"),
                            ("CAPACITACION", "Capacitación"),
                            ("OTRA", "Otra"),
                        ],
                        db_column="tipoActividad",
                        max_length=20,
                    ),
                ),
                (
                    "fecha_estimada",
                    models.DateField(db_column="fechaEstimada"),
                ),
                (
                    "horario_inicio_estimado",
                    models.TimeField(db_column="horarioInicioEstimado"),
                ),
                (
                    "horario_fin_estimado",
                    models.TimeField(db_column="horarioFinEstimado"),
                ),
                (
                    "participantes_estimados",
                    models.PositiveIntegerField(
                        db_column="participantesEstimados",
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "requerimiento_espacio",
                    models.TextField(
                        blank=True,
                        db_column="requerimientoEspacio",
                        default="",
                    ),
                ),
                (
                    "equipamiento_necesario",
                    models.TextField(
                        blank=True,
                        db_column="equipamientoNecesario",
                        default="",
                    ),
                ),
                (
                    "responsable",
                    models.ForeignKey(
                        db_column="idResponsable",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actividades_responsable",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Actividad",
                "verbose_name_plural": "Actividades",
                "db_table": "actividad",
                "ordering": ["fecha_estimada", "horario_inicio_estimado"],
            },
        ),
        migrations.AddField(
            model_name="reserva",
            name="actividad",
            field=models.ForeignKey(
                db_column="idActividad",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reservas",
                to="reservas.actividad",
            ),
        ),
        migrations.RunPython(
            copiar_reserva_a_actividad,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="reserva",
            name="nombre_actividad",
        ),
        migrations.RemoveField(
            model_name="reserva",
            name="tipo_actividad",
        ),
        migrations.AlterField(
            model_name="reserva",
            name="actividad",
            field=models.ForeignKey(
                db_column="idActividad",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reservas",
                to="reservas.actividad",
            ),
        ),
    ]

