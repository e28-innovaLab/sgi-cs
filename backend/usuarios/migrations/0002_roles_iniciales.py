from django.db import migrations


def crear_roles(apps, schema_editor):
    rol = apps.get_model('usuarios', 'Rol')
    for nombre in ['ADMIN', 'COORDINACION']:
        rol.objects.using(schema_editor.connection.alias).get_or_create(nombre=nombre)


class Migration(migrations.Migration):
    dependencies = [('usuarios', '0001_initial')]
    operations = [migrations.RunPython(crear_roles, migrations.RunPython.noop)]
