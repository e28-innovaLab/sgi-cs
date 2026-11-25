import csv
from collections.abc import Mapping
from io import StringIO

from django.db import IntegrityError
from django.http import Http404, HttpResponse
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.permissions import SoloAdministrador
from .reader import ArchivoInvalido, DependenciaExcelNoDisponible, MAX_BYTES, MAX_FILAS, leer_archivo
from .schemas import COLUMNAS
from .services import procesar_importacion


class ArchivoSerializer(serializers.Serializer):
    archivo = serializers.FileField(max_length=255, allow_empty_file=False)
    confirmar = serializers.BooleanField(default=False)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            desconocidos = set(data) - set(self.fields)
            if desconocidos:
                raise serializers.ValidationError({k: 'Campo no admitido.' for k in sorted(desconocidos)})
        return super().to_internal_value(data)


class ImportacionView(APIView):
    permission_classes = [SoloAdministrador]
    parser_classes = [MultiPartParser, FormParser]
    tipo = None

    def get(self, request):
        if self.tipo not in COLUMNAS:
            raise Http404
        return Response({
            'recurso': self.tipo, 'columnas': COLUMNAS[self.tipo],
            'formatos': ['csv', 'xlsx'], 'max_bytes': MAX_BYTES, 'max_filas': MAX_FILAS,
            'confirmar_por_defecto': False, 'politica': 'Solo altas; los existentes no se modifican.',
        })

    def post(self, request):
        if self.tipo not in COLUMNAS:
            raise Http404
        serializer = ArchivoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            filas = leer_archivo(serializer.validated_data['archivo'], self.tipo)
            resultado = procesar_importacion(self.tipo, filas, serializer.validated_data['confirmar'])
        except DependenciaExcelNoDisponible as exc:
            return Response({'archivo': [str(exc)]}, status=503)
        except ArchivoInvalido as exc:
            return Response({'archivo': [str(exc)]}, status=400)
        except IntegrityError:
            return Response({'detail': 'Los datos cambiaron durante la carga. No se importó ninguna fila; volvé a validar el archivo.'}, status=409)
        estado = 400 if resultado['resumen']['errores'] else 201 if resultado['resumen']['creadas'] else 200
        return Response(resultado, status=estado)


class PlantillaImportacionView(APIView):
    permission_classes = [SoloAdministrador]
    tipo = None

    def get(self, request):
        if self.tipo not in COLUMNAS:
            raise Http404
        esquema = COLUMNAS[self.tipo]
        salida = StringIO(newline='')
        csv.writer(salida).writerow(esquema['obligatorias'] + esquema['opcionales'])
        respuesta = HttpResponse(salida.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        respuesta['Content-Disposition'] = f'attachment; filename="plantilla_{self.tipo}.csv"'
        return respuesta
