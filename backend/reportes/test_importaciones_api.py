import csv
from io import BytesIO, StringIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from espacios.models import Aula, Categoria, Equipamiento
from espacios.serializers import AulaSerializer
from usuarios.models import Rol, Usuario


class ImportacionesAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.roles = {
            nombre: Rol.objects.get_or_create(nombre=nombre)[0]
            for nombre in ['ADMIN', 'COORDINACION', 'SOLICITANTE']
        }
        cls.admin = Usuario.objects.create_user(
            username='importador', numero_documento='import-1', rol=cls.roles['ADMIN'],
        )
        cls.otro = Usuario.objects.create_user(
            username='lector', numero_documento='import-2', rol=cls.roles['COORDINACION'],
        )
        cls.categoria = Categoria.objects.create(nombre='Tecnología')
        cls.aula = Aula.objects.create(nombre='Laboratorio existente', capacidad=25)

    def setUp(self):
        self.client.force_authenticate(self.admin)

    @staticmethod
    def url(recurso='aulas'):
        return f'/api/importaciones/{recurso}/'

    @staticmethod
    def archivo(texto, nombre='catalogo.csv'):
        return SimpleUploadedFile(nombre, texto.encode('utf-8'), content_type='text/csv')

    def enviar(self, texto, recurso='aulas', confirmar=None, **extra):
        datos = {'archivo': self.archivo(texto), **extra}
        if confirmar is not None:
            datos['confirmar'] = confirmar
        return self.client.post(self.url(recurso), datos, format='multipart')

    @staticmethod
    def archivo_excel(filas):
        from openpyxl import Workbook
        libro = Workbook()
        for fila in filas:
            libro.active.append(fila)
        contenido = BytesIO()
        libro.save(contenido)
        libro.close()
        return SimpleUploadedFile(
            'catalogo.xlsx', contenido.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_autenticacion_obligatoria_para_carga_ayuda_y_plantillas(self):
        self.client.force_authenticate(None)
        for recurso in ['aulas', 'equipamientos']:
            with self.subTest(recurso=recurso):
                self.assertEqual(self.client.get(self.url(recurso)).status_code, 401)
                self.assertEqual(self.enviar('nombre,capacidad\nNueva,20\n', recurso).status_code, 401)
                self.assertEqual(self.client.get(f'/api/importaciones/plantillas/{recurso}/').status_code, 401)

    def test_solo_administracion_puede_acceder(self):
        for rol in ['COORDINACION', 'SOLICITANTE']:
            self.otro.rol = self.roles[rol]
            self.otro.save(update_fields=['rol'])
            self.client.force_authenticate(self.otro)
            for recurso in ['aulas', 'equipamientos']:
                with self.subTest(rol=rol, recurso=recurso):
                    self.assertEqual(self.client.get(self.url(recurso)).status_code, 403)
                    self.assertEqual(self.enviar('nombre,capacidad\nNueva,20\n', recurso, 'true').status_code, 403)
                    self.assertEqual(self.client.get(f'/api/importaciones/plantillas/{recurso}/').status_code, 403)
        self.assertFalse(Aula.objects.filter(nombre='Nueva').exists())

    def test_autenticacion_real_por_token_y_usuario_inactivo(self):
        token = Token.objects.create(user=self.admin)
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.admin.is_active = False
        self.admin.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(self.url()).status_code, 401)

    def test_superusuario_activo_puede_acceder(self):
        superusuario = Usuario.objects.create_superuser(
            username='import_super', numero_documento='import-3', password='PruebaSegura!456',
        )
        self.client.force_authenticate(superusuario)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_no_se_habilita_edicion_por_put_patch_ni_delete(self):
        for metodo in [self.client.put, self.client.patch, self.client.delete]:
            with self.subTest(metodo=metodo.__name__):
                self.assertEqual(metodo(self.url(), {}, format='json').status_code, 405)

    def test_plantillas_contienen_encabezados_csv(self):
        for recurso, requeridos in [
            ('aulas', {'nombre', 'capacidad'}),
            ('equipamientos', {'nombre', 'categoria', 'cantidad', 'trasladable'}),
        ]:
            with self.subTest(recurso=recurso):
                respuesta = self.client.get(f'/api/importaciones/plantillas/{recurso}/')
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('text/csv', respuesta['Content-Type'])
                lineas = list(csv.reader(StringIO(respuesta.content.decode('utf-8-sig'))))
                self.assertTrue(requeridos.issubset(set(lineas[0])))
                self.assertNotIn(self.aula.nombre, respuesta.content.decode('utf-8-sig'))

    def test_tipo_inexistente_no_tiene_endpoint(self):
        self.assertEqual(self.client.get(self.url('usuarios')).status_code, 404)
        self.assertEqual(self.client.get('/api/importaciones/plantillas/usuarios/').status_code, 404)

    def test_por_defecto_solo_valida_sin_escribir(self):
        antes = Aula.objects.count()
        respuesta = self.enviar('nombre,capacidad\nAula de importación,20\n')
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data['recurso'], 'aulas')
        self.assertEqual(respuesta.data['modo'], 'validacion')
        self.assertEqual(respuesta.data['resumen']['filas'], 1)
        self.assertEqual(respuesta.data['resumen']['por_crear'], 1)
        self.assertEqual(respuesta.data['resumen']['creadas'], 0)
        self.assertEqual(respuesta.data['filas'][0]['fila'], 2)
        self.assertEqual(respuesta.data['filas'][0]['accion'], 'crear')
        self.assertEqual(Aula.objects.count(), antes)

    def test_confirmar_crea_aulas_con_datos_y_defaults_del_modelo(self):
        respuesta = self.enviar(
            'nombre,capacidad,tipo,sillas,mesas\nSala nueva,32,LABORATORIO,30,8\n', confirmar='true',
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data['modo'], 'importacion')
        self.assertEqual(respuesta.data['resumen']['creadas'], 1)
        aula = Aula.objects.get(nombre='Sala nueva')
        self.assertEqual((aula.capacidad, aula.tipo, aula.sillas, aula.mesas), (32, 'LABORATORIO', 30, 8))
        self.assertEqual(aula.estado, 'DISPONIBLE')

    def test_error_por_fila_impide_toda_la_carga(self):
        antes = Aula.objects.count()
        respuesta = self.enviar('nombre,capacidad\nAula válida,20\nAula inválida,0\n', confirmar='true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(respuesta.data['resumen']['creadas'], 0)
        self.assertEqual(respuesta.data['resumen']['errores'], 1)
        error = next(f for f in respuesta.data['filas'] if f['accion'] == 'error')
        self.assertEqual(error['fila'], 3)
        self.assertIn('capacidad', error['errores'])
        self.assertEqual(Aula.objects.count(), antes)

    def test_reimportar_mismo_archivo_no_duplica_aulas(self):
        texto = 'nombre,capacidad\nRepetible,20\n'
        self.assertEqual(self.enviar(texto, confirmar='true').status_code, 201)
        respuesta = self.enviar(texto, confirmar='true')
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data['resumen']['creadas'], 0)
        self.assertEqual(respuesta.data['resumen']['omitidas'], 1)
        self.assertEqual(Aula.objects.filter(nombre='Repetible').count(), 1)

    def test_aula_existente_distinta_se_informa_sin_actualizar(self):
        texto = f'nombre,capacidad\n{self.aula.nombre},99\n'
        respuesta = self.enviar(texto, confirmar='true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(respuesta.data['resumen']['errores'], 1)
        self.aula.refresh_from_db()
        self.assertEqual(self.aula.capacidad, 25)

    def test_duplicados_dentro_del_archivo_impiden_carga(self):
        respuesta = self.enviar('nombre,capacidad\nDuplicada,20\nDuplicada,20\n', confirmar='true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertGreaterEqual(respuesta.data['resumen']['errores'], 1)
        self.assertFalse(Aula.objects.filter(nombre='Duplicada').exists())

    def test_crea_equipo_fijo_con_relaciones_por_nombre(self):
        texto = (f'nombre,categoria,cantidad,trasladable,aula\n'
                 f'Simulador,{self.categoria.nombre},2,no,{self.aula.nombre}\n')
        respuesta = self.enviar(texto, recurso='equipamientos', confirmar='true')
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        equipo = Equipamiento.objects.get(nombre='Simulador')
        self.assertEqual(equipo.categoria_id, self.categoria.pk)
        self.assertEqual(equipo.aula_id, self.aula.pk)
        self.assertEqual(equipo.cantidad, 2)
        self.assertFalse(equipo.trasladable)

    def test_equipo_fijo_sin_aula_es_error_de_fila(self):
        texto = f'nombre,categoria,cantidad,trasladable\nFijo,{self.categoria.nombre},1,false\n'
        respuesta = self.enviar(texto, recurso='equipamientos', confirmar='true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertIn('aula', respuesta.data['filas'][0]['errores'])
        self.assertFalse(Equipamiento.objects.exists())

    def test_valores_booleanos_admitidos_para_equipos(self):
        for indice, (valor, esperado) in enumerate([
            ('true', True), ('1', True), ('si', True), ('sí', True),
            ('false', False), ('0', False), ('no', False),
        ]):
            with self.subTest(valor=valor):
                nombre = f'Equipo booleano {indice}'
                texto = (f'nombre,categoria,cantidad,trasladable,aula\n'
                         f'{nombre},{self.categoria.nombre},1,{valor},{self.aula.nombre}\n')
                respuesta = self.enviar(texto, recurso='equipamientos', confirmar='true')
                self.assertEqual(respuesta.status_code, 201, respuesta.data)
                self.assertEqual(Equipamiento.objects.get(nombre=nombre).trasladable, esperado)

    def test_relaciones_desconocidas_no_se_crean_implicitamente(self):
        antes_categorias = Categoria.objects.count()
        antes_aulas = Aula.objects.count()
        for texto, campo in [
            ('nombre,categoria,cantidad,trasladable\nMóvil,No existe,1,true\n', 'categoria'),
            (f'nombre,categoria,cantidad,trasladable,aula\nFijo,{self.categoria.nombre},1,false,No existe\n', 'aula'),
        ]:
            with self.subTest(campo=campo):
                respuesta = self.enviar(texto, recurso='equipamientos', confirmar='true')
                self.assertEqual(respuesta.status_code, 400, respuesta.data)
                self.assertIn(campo, respuesta.data['filas'][0]['errores'])
        self.assertEqual(Categoria.objects.count(), antes_categorias)
        self.assertEqual(Aula.objects.count(), antes_aulas)
        self.assertFalse(Equipamiento.objects.exists())

    def test_reimportar_equipo_no_duplica_ni_cambia_stock(self):
        texto = f'nombre,categoria,cantidad,trasladable\nNotebooks,{self.categoria.nombre},5,true\n'
        self.assertEqual(self.enviar(texto, 'equipamientos', 'true').status_code, 201)
        respuesta = self.enviar(texto, 'equipamientos', 'true')
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data['resumen']['omitidas'], 1)
        distinto = texto.replace(',5,true', ',9,true')
        respuesta = self.enviar(distinto, 'equipamientos', 'true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(Equipamiento.objects.get(nombre='Notebooks').cantidad, 5)
        self.assertEqual(Equipamiento.objects.count(), 1)

    def test_importa_excel_con_valores_nativos(self):
        archivo = self.archivo_excel([
            ['nombre', 'categoria', 'cantidad', 'trasladable'],
            ['Móvil Excel', self.categoria.nombre, 3, True],
        ])
        respuesta = self.client.post(self.url('equipamientos'), {
            'archivo': archivo, 'confirmar': 'true',
        }, format='multipart')
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        equipo = Equipamiento.objects.get(nombre='Móvil Excel')
        self.assertEqual(equipo.cantidad, 3)
        self.assertTrue(equipo.trasladable)

    def test_excel_con_formula_se_rechaza_sin_crear_datos(self):
        archivo = self.archivo_excel([['nombre', 'capacidad'], ['Con fórmula', '=10+10']])
        antes = Aula.objects.count()
        respuesta = self.client.post(self.url(), {'archivo': archivo, 'confirmar': 'true'}, format='multipart')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(Aula.objects.count(), antes)

    def test_validacion_de_archivo_y_parametros(self):
        casos = [
            {},
            {'archivo': self.archivo('nombre,capacidad\nAula,20\n'), 'confirmar': 'quizás'},
            {'archivo': self.archivo('nombre,capacidad\nAula,20\n'), 'usuario': 'otro'},
            {'archivo': self.archivo('contenido', 'catalogo.xls')},
            {'archivo': self.archivo('nombre,capacidad,clave\nAula,20,secreto\n')},
        ]
        for datos in casos:
            with self.subTest(campos=list(datos)):
                self.assertEqual(self.client.post(self.url(), datos, format='multipart').status_code, 400)
        self.assertFalse(Aula.objects.filter(nombre='Aula').exists())

    def test_rechaza_archivo_mayor_a_dos_mib(self):
        archivo = SimpleUploadedFile('grande.csv', b'x' * (2 * 1024 * 1024 + 1), content_type='text/csv')
        antes = Aula.objects.count()
        respuesta = self.client.post(self.url(), {'archivo': archivo, 'confirmar': 'true'}, format='multipart')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(Aula.objects.count(), antes)

    def test_rechaza_mas_de_mil_filas_sin_cargas_parciales(self):
        texto = 'nombre,capacidad\n' + ''.join(f'Aula {indice},20\n' for indice in range(1001))
        antes = Aula.objects.count()
        respuesta = self.enviar(texto, confirmar='true')
        self.assertEqual(respuesta.status_code, 400, respuesta.data)
        self.assertEqual(Aula.objects.count(), antes)

    def test_fallo_durante_guardado_revierte_tambien_las_primeras_altas(self):
        antes = Aula.objects.count()
        crear_original = AulaSerializer.create
        llamadas = []

        def crear_o_fallar(serializer, datos):
            llamadas.append(datos['nombre'])
            if len(llamadas) == 2:
                raise IntegrityError('Conflicto concurrente simulado')
            return crear_original(serializer, datos)

        with patch('reportes.importaciones.services.AulaSerializer.create', autospec=True,
                   side_effect=crear_o_fallar):
            respuesta = self.enviar(
                'nombre,capacidad\nPrimera de transacción,20\nSegunda de transacción,30\n',
                confirmar='true',
            )
        self.assertEqual(respuesta.status_code, 409, respuesta.data)
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(Aula.objects.count(), antes)
        self.assertFalse(Aula.objects.filter(nombre='Primera de transacción').exists())
