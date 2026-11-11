from django.db import migrations


def crear_rol_solicitante(apps, schema_editor):
    Rol = apps.get_model('usuarios', 'Rol')

    Rol.objects.using(schema_editor.connection.alias).get_or_create(
        nombre='SOLICITANTE'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_alter_usuario_managers'),
    ]

    operations = [
        migrations.RunPython(
            crear_rol_solicitante,
            migrations.RunPython.noop,
        ),
    ]