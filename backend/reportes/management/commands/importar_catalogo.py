import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.core.serializers.json import DjangoJSONEncoder

from reportes.importaciones.reader import ArchivoInvalido, leer_archivo
from reportes.importaciones.services import procesar_importacion


class Command(BaseCommand):
    help = 'Valida CSV/XLSX de aulas o equipos. Solo crea registros al usar --confirmar.'

    def add_arguments(self, parser):
        parser.add_argument('recurso', choices=['aulas', 'equipamientos'])
        parser.add_argument('archivo', type=Path)
        parser.add_argument('--confirmar', action='store_true')

    def handle(self, *args, **options):
        try:
            with options['archivo'].open('rb') as archivo:
                filas = leer_archivo(archivo, options['recurso'])
            resultado = procesar_importacion(options['recurso'], filas, options['confirmar'])
        except (OSError, ArchivoInvalido) as exc:
            raise CommandError(str(exc)) from exc
        except IntegrityError as exc:
            raise CommandError('Los datos cambiaron durante la carga. No se importó ninguna fila; volvé a validar.') from exc
        self.stdout.write(json.dumps(resultado, ensure_ascii=False, cls=DjangoJSONEncoder))
        if resultado['resumen']['errores']:
            raise CommandError('La validación encontró filas con errores. No se importó ninguna fila.')
