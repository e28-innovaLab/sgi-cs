from io import BytesIO
import importlib.util
import sys
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .reader import (
    ArchivoInvalido, DependenciaExcelNoDisponible, MAX_BYTES, leer_archivo,
)


class LecturaCSVTests(SimpleTestCase):
    def archivo(self, texto, nombre='datos.csv'):
        return SimpleUploadedFile(nombre, texto.encode('utf-8'))

    def test_lee_coma_utf8_bom_y_normaliza_encabezados(self):
        archivo = self.archivo('\ufeff NOMBRE , CAPACIDAD , Ubicación\n Laboratorio ,20, Planta baja \n')
        self.assertEqual(leer_archivo(archivo, 'aulas'), [{
            'fila': 2, 'datos': {'nombre': 'Laboratorio', 'capacidad': '20', 'ubicacion': 'Planta baja'},
        }])

    def test_lee_punto_y_coma_omite_blancos_y_mantiene_filas_reales(self):
        archivo = self.archivo('nombre;capacidad;color\n\n Aula 1 ;10;\n;;\nAula 2;20;azul\n')
        self.assertEqual(leer_archivo(archivo, 'aulas'), [
            {'fila': 3, 'datos': {'nombre': 'Aula 1', 'capacidad': '10'}},
            {'fila': 5, 'datos': {'nombre': 'Aula 2', 'capacidad': '20', 'color': 'azul'}},
        ])

    def test_respeta_comillas_separadores_y_saltos_dentro_de_celda(self):
        archivo = self.archivo('nombre,capacidad\n"Aula, grande\ncontinua",20\nOtra,10\n')
        filas = leer_archivo(archivo, 'aulas')
        self.assertEqual(filas[0]['fila'], 2)
        self.assertEqual(filas[0]['datos']['nombre'], 'Aula, grande\ncontinua')
        self.assertEqual(filas[1]['fila'], 4)

    def test_no_convierte_datos_del_modelo_en_el_lector(self):
        archivo = self.archivo('nombre,categoria,cantidad,trasladable,aula\nNotebook,Tecnologia,10,si,\n')
        self.assertEqual(leer_archivo(archivo, 'equipamientos'), [{
            'fila': 2, 'datos': {'nombre': 'Notebook', 'categoria': 'Tecnologia',
                                'cantidad': '10', 'trasladable': 'si'},
        }])

    def test_rechaza_encabezados_repetidos_desconocidos_o_faltantes(self):
        for texto in [
            'nombre,Nombre,capacidad\nA,B,10',
            'nombre,capacidad,desconocido\nA,10,x',
            'nombre\nA',
            'nombre,capacidad,\nA,10,x',
        ]:
            with self.subTest(texto=texto), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.archivo(texto), 'aulas')

    def test_rechaza_columnas_desajustadas_y_comillas_sin_cerrar(self):
        for texto in ['nombre,capacidad\nA,10,x', 'nombre,capacidad\nA',
                      'nombre,capacidad\n"A,10']:
            with self.subTest(texto=texto), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.archivo(texto), 'aulas')

    def test_rechaza_vacio_sin_datos_y_codificacion_invalida(self):
        for contenido in [b'', b'nombre,capacidad\n', b'nombre,capacidad\n\n,\n',
                          b'nombre,capacidad\nA\xff,10', b'nombre\x00,capacidad\nA,10']:
            with self.subTest(contenido=contenido), self.assertRaises(ArchivoInvalido):
                leer_archivo(SimpleUploadedFile('aulas.csv', contenido), 'aulas')

    def test_rechaza_extension_tipo_y_tamano_no_admitidos(self):
        for nombre in ['aulas.xls', 'aulas.xlsm', 'aulas.txt', 'aulas']:
            with self.subTest(nombre=nombre), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.archivo('nombre,capacidad\nA,10', nombre), 'aulas')
        with self.assertRaises(ArchivoInvalido):
            leer_archivo(self.archivo('nombre,capacidad\nA,10'), 'usuarios')
        with self.assertRaisesMessage(ArchivoInvalido, '2 MiB'):
            leer_archivo(SimpleUploadedFile('grande.csv', b'x' * (MAX_BYTES + 1)), 'aulas')

    def test_limita_filas_datos_y_columnas(self):
        mil = 'nombre,capacidad\n' + ''.join(f'Aula {i},10\n' for i in range(1000))
        self.assertEqual(len(leer_archivo(self.archivo(mil), 'aulas')), 1000)
        with self.assertRaisesMessage(ArchivoInvalido, '1000'):
            leer_archivo(self.archivo(mil + 'Extra,10\n'), 'aulas')
        with self.assertRaisesMessage(ArchivoInvalido, '16'):
            leer_archivo(self.archivo(','.join(f'col{i}' for i in range(17)) + '\n'), 'aulas')

    def test_csv_funciona_sin_dependencia_excel(self):
        with patch.dict(sys.modules, {'openpyxl': None}):
            self.assertEqual(len(leer_archivo(self.archivo('nombre,capacidad\nA,10'), 'aulas')), 1)
            with self.assertRaises(DependenciaExcelNoDisponible):
                leer_archivo(SimpleUploadedFile('datos.xlsx', b'no importa'), 'aulas')


class LecturaExcelTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if importlib.util.find_spec('openpyxl') is None:
            from unittest import SkipTest
            raise SkipTest('El lector XLSX requiere requirements-importacion.txt.')

    def libro(self, filas, modificar=None):
        from openpyxl import Workbook
        libro = Workbook()
        hoja = libro.active
        for fila in filas:
            hoja.append(fila)
        if modificar:
            modificar(libro)
        buffer = BytesIO()
        libro.save(buffer)
        libro.close()
        return SimpleUploadedFile('catalogo.xlsx', buffer.getvalue())

    def reemplazar_zip(self, archivo, entrada, transformacion):
        original = ZipFile(BytesIO(archivo.read()))
        buffer = BytesIO()
        with original, ZipFile(buffer, 'w', ZIP_DEFLATED) as nuevo:
            for info in original.infolist():
                contenido = original.read(info.filename)
                if info.filename == entrada:
                    contenido = transformacion(contenido)
                nuevo.writestr(info.filename, contenido)
        return SimpleUploadedFile('catalogo.xlsx', buffer.getvalue())

    def test_lee_valores_nativos_y_omite_filas_y_celdas_opcionales_vacias(self):
        archivo = self.libro([
            ['nombre', 'categoria', 'cantidad', 'trasladable', 'aula'],
            ['Notebook', 'Tecnologia', 10, True, None], [],
            ['Fijo', 'Tecnologia', 1, False, 'Aula 1'],
        ])
        self.assertEqual(leer_archivo(archivo, 'equipamientos'), [
            {'fila': 2, 'datos': {'nombre': 'Notebook', 'categoria': 'Tecnologia', 'cantidad': 10, 'trasladable': True}},
            {'fila': 4, 'datos': {'nombre': 'Fijo', 'categoria': 'Tecnologia', 'cantidad': 1, 'trasladable': False, 'aula': 'Aula 1'}},
        ])

    def test_rechaza_formulas_y_errores_de_celda(self):
        for valor in ['=1+1', '#DIV/0!']:
            with self.subTest(valor=valor), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.libro([['nombre', 'capacidad'], ['Aula', valor]]), 'aulas')

    def test_rechaza_multiples_hojas_y_libro_danado(self):
        with self.assertRaisesMessage(ArchivoInvalido, 'una sola hoja'):
            leer_archivo(self.libro([['nombre', 'capacidad'], ['A', 10]],
                                   lambda libro: libro.create_sheet('Otra')), 'aulas')
        with self.assertRaises(ArchivoInvalido):
            leer_archivo(SimpleUploadedFile('catalogo.xlsx', b'no es zip'), 'aulas')

    def test_no_confia_en_dimensiones_incorrectas_del_excel(self):
        archivo = self.libro([['nombre', 'capacidad'], ['Aula 1', 10], ['Aula 2', 20]])
        archivo = self.reemplazar_zip(archivo, 'xl/worksheets/sheet1.xml',
                                     lambda xml: xml.replace(b'ref="A1:B3"', b'ref="A1:A1"'))
        self.assertEqual(len(leer_archivo(archivo, 'aulas')), 2)

    def test_rechaza_filas_dispersas_y_columnas_fuera_del_limite(self):
        for modificar in [lambda libro: libro.active.cell(row=1002, column=1, value='Extra'),
                           lambda libro: libro.active.cell(row=2, column=17, value='Extra')]:
            with self.subTest(modificar=modificar), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.libro([['nombre', 'capacidad'], ['A', 10]], modificar), 'aulas')

    def test_rechaza_datos_fuera_de_encabezados_y_encabezados_invalidos(self):
        for filas in [
            [['nombre', 'capacidad'], ['Aula', 10, 'extra']],
            [['nombre', 'nombre', 'capacidad'], ['Aula', 'Aula', 10]],
            [['nombre', 'desconocida'], ['Aula', 10]],
        ]:
            with self.subTest(filas=filas), self.assertRaises(ArchivoInvalido):
                leer_archivo(self.libro(filas), 'aulas')

    def test_rechaza_declaraciones_dtd_y_contenido_expandido_excesivo(self):
        archivo = self.libro([['nombre', 'capacidad'], ['A', 10]])
        archivo = self.reemplazar_zip(archivo, 'xl/worksheets/sheet1.xml',
                                     lambda xml: b'<!DOCTYPE x [<!ENTITY x "a">]>' + xml)
        with self.assertRaisesMessage(ArchivoInvalido, 'XML no admitidas'):
            leer_archivo(archivo, 'aulas')
        buffer = BytesIO()
        with ZipFile(buffer, 'w', ZIP_DEFLATED) as zipfile:
            zipfile.writestr('xl/worksheets/sheet1.xml', b'x' * (20 * 1024 * 1024 + 1))
        with self.assertRaisesMessage(ArchivoInvalido, '20 MiB'):
            leer_archivo(SimpleUploadedFile('grande.xlsx', buffer.getvalue()), 'aulas')
