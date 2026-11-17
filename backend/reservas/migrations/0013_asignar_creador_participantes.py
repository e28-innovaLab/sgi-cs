from django.conf import settings
from django.db import migrations


def asignar_creador(apps, schema_editor):
    Participante = apps.get_model("reservas", "Participante")
    Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    participantes_sin_creador = Participante.objects.filter(
        creado_por__isnull=True
    )

    # Si no hay participantes pendientes de asignación,
    # no necesitamos buscar un administrador.
    if not participantes_sin_creador.exists():
        return

    administrador = (
        Usuario.objects
        .filter(rol__nombre="ADMIN")
        .order_by("pk")
        .first()
    )

    if administrador is None:
        raise RuntimeError(
            "Existen participantes sin creador, pero no hay "
            "un usuario con rol ADMIN para asignarles."
        )

    participantes_sin_creador.update(creado_por=administrador)


class Migration(migrations.Migration):

    dependencies = [
        ("reservas", "0012_participante_creado_por"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            asignar_creador,
            migrations.RunPython.noop,
        ),
    ]