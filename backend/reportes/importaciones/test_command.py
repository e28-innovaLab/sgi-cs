import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from espacios.models import Aula


class ComandoImportacionTests(TestCase):
    def test_validacion_confirmacion_y_repeticion_desde_consola(self):
        with TemporaryDirectory(prefix='siges-importacion-') as carpeta:
            archivo = Path(carpeta) / 'carga de aulas.csv'
            archivo.write_text('nombre,capacidad\nSala de consola,20\n', encoding='utf-8')
            salida = StringIO()
            call_command('importar_catalogo', 'aulas', str(archivo), stdout=salida)
            self.assertEqual(json.loads(salida.getvalue())['resumen']['por_crear'], 1)
            self.assertFalse(Aula.objects.exists())
            salida = StringIO()
            call_command('importar_catalogo', 'aulas', str(archivo), confirmar=True, stdout=salida)
            self.assertEqual(json.loads(salida.getvalue())['resumen']['creadas'], 1)
            salida = StringIO()
            call_command('importar_catalogo', 'aulas', str(archivo), confirmar=True, stdout=salida)
            self.assertEqual(json.loads(salida.getvalue())['resumen']['omitidas'], 1)
            self.assertEqual(Aula.objects.count(), 1)

    def test_errores_por_fila_cancelan_la_carga_completa(self):
        with TemporaryDirectory(prefix='siges-importacion-') as carpeta:
            archivo = Path(carpeta) / 'datos.csv'
            archivo.write_text('nombre,capacidad\nPrimera,20\nSegunda,-1\n', encoding='utf-8')
            salida = StringIO()
            with self.assertRaisesMessage(CommandError, 'No se importó ninguna fila'):
                call_command('importar_catalogo', 'aulas', str(archivo), confirmar=True, stdout=salida)
            datos = json.loads(salida.getvalue())
            self.assertEqual(datos['resumen']['creadas'], 0)
            self.assertEqual(datos['resumen']['errores'], 1)
            self.assertEqual(datos['filas'][1]['fila'], 3)
            self.assertFalse(Aula.objects.exists())

    def test_archivo_inexistente_informa_error_sin_escrituras(self):
        with TemporaryDirectory(prefix='siges-importacion-') as carpeta:
            with self.assertRaises(CommandError):
                call_command('importar_catalogo', 'aulas', str(Path(carpeta) / 'no-existe.csv'))
            self.assertFalse(Aula.objects.exists())
