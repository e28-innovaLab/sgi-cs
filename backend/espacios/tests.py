from rest_framework.test import APITestCase

from usuarios.models import Rol, Usuario
from .models import Aula, Categoria, Equipamiento


class CatalogosAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user(
            username='admin', rol=Rol.objects.get(nombre=Rol.ADMIN), numero_documento='100',
        )
        cls.coordinacion = Usuario.objects.create_user(
            username='coord', rol=Rol.objects.get(nombre=Rol.COORDINACION), numero_documento='101',
        )
        cls.aula = Aula.objects.create(nombre='Aula 1', capacidad=20)
        cls.categoria = Categoria.objects.create(nombre='Simuladores')
        cls.equipo = Equipamiento.objects.create(
            nombre='Simulador', categoria=cls.categoria, aula=cls.aula,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_admin_gestiona_aulas(self):
        response = self.client.post('/api/aulas/', {
            'nombre': 'Laboratorio', 'capacidad': 25, 'tipo': 'LABORATORIO',
            'ubicacion': 'Planta baja', 'caracteristicas': 'Área de prácticas',
        })
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/aulas/{response.data['id_aula']}/"
        self.assertEqual(self.client.get(url).data['estado'], 'DISPONIBLE')
        self.assertEqual(self.client.patch(url, {'capacidad': 30}).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_admin_gestiona_categorias_y_equipos(self):
        categoria = self.client.post('/api/categorias/', {'nombre': 'Tecnología'})
        self.assertEqual(categoria.status_code, 201)
        response = self.client.post('/api/equipamientos/', {
            'nombre': 'Notebooks', 'cantidad': 10, 'trasladable': True,
            'categoria': categoria.data['id_categoria'],
        })
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/equipamientos/{response.data['id_equipo']}/"
        self.assertEqual(self.client.patch(url, {'aula': self.aula.pk}).status_code, 200)
        self.assertEqual(self.client.get(url).data['aula_nombre'], 'Aula 1')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(f"/api/categorias/{categoria.data['id_categoria']}/").status_code, 204)

    def test_validaciones_de_aulas(self):
        for cambios in [
            {'capacidad': 0}, {'capacidad': -1}, {'sillas': -1},
            {'mesas': -1}, {'tipo': 'DESCONOCIDO'}, {'estado': 'OCUPADA'},
            {'nombre': 'Aula 1'},
        ]:
            with self.subTest(cambios=cambios):
                response = self.client.post('/api/aulas/', {'nombre': 'Otra', 'capacidad': 10, **cambios})
                self.assertEqual(response.status_code, 400)

    def test_equipamiento_fijo_requiere_ubicacion_incluso_en_patch(self):
        datos = {'nombre': 'Fijo', 'categoria': self.categoria.pk, 'trasladable': False}
        self.assertEqual(self.client.post('/api/equipamientos/', datos).status_code, 400)
        self.assertEqual(self.client.patch(f'/api/equipamientos/{self.equipo.pk}/', {'aula': None}, format='json').status_code, 400)
        response = self.client.patch(
            f'/api/equipamientos/{self.equipo.pk}/', {'trasladable': True, 'aula': None}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.patch(f'/api/equipamientos/{self.equipo.pk}/', {'trasladable': False}).status_code, 400)

    def test_cantidades_estado_y_relaciones_de_equipo_se_validan(self):
        for cambios in [{'cantidad': 0}, {'cantidad': -1}, {'estado': None}, {'estado': 'ROTO'}, {'categoria': 99999}, {'aula': 99999}]:
            with self.subTest(cambios=cambios):
                response = self.client.patch(f'/api/equipamientos/{self.equipo.pk}/', cambios, format='json')
                self.assertEqual(response.status_code, 400)

    def test_coordinacion_consulta_catalogos_pero_no_los_configura(self):
        self.client.force_authenticate(self.coordinacion)
        for ruta, pk in [('aulas', self.aula.pk), ('equipamientos', self.equipo.pk), ('categorias', self.categoria.pk)]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(f'/api/{ruta}/').status_code, 200)
                self.assertEqual(self.client.get(f'/api/{ruta}/{pk}/').status_code, 200)
                self.assertEqual(self.client.post(f'/api/{ruta}/', {}).status_code, 403)
                self.assertEqual(self.client.patch(f'/api/{ruta}/{pk}/', {'nombre': 'Cambio'}).status_code, 403)
                self.assertEqual(self.client.put(f'/api/{ruta}/{pk}/', {}).status_code, 403)
                self.assertEqual(self.client.delete(f'/api/{ruta}/{pk}/').status_code, 403)

    def test_coordinacion_actualiza_solo_estado(self):
        self.client.force_authenticate(self.coordinacion)
        for ruta, objeto in [('aulas', self.aula), ('equipamientos', self.equipo)]:
            with self.subTest(ruta=ruta):
                url = f'/api/{ruta}/{objeto.pk}/estado/'
                self.assertEqual(self.client.patch(url, {'estado': 'MANTENIMIENTO'}).status_code, 200)
                objeto.refresh_from_db()
                self.assertEqual(objeto.estado, 'MANTENIMIENTO')
                self.assertEqual(self.client.patch(url, {}).status_code, 400)
                self.assertEqual(self.client.patch(url, {'estado': 'ROTO'}).status_code, 400)
                self.assertEqual(self.client.patch(url, {'estado': 'DISPONIBLE', 'nombre': 'Cambio'}).status_code, 400)
                objeto.refresh_from_db()
                self.assertEqual(objeto.estado, 'MANTENIMIENTO')

    def test_no_se_eliminan_categorias_en_uso_ni_aulas_con_equipo(self):
        self.assertEqual(self.client.delete(f'/api/categorias/{self.categoria.pk}/').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/aulas/{self.aula.pk}/').status_code, 409)
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())
        self.assertTrue(Aula.objects.filter(pk=self.aula.pk).exists())
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.aula, self.aula)

    def test_filtros_y_busqueda_de_aulas(self):
        Aula.objects.create(nombre='Laboratorio', tipo='LABORATORIO', capacidad=40)
        response = self.client.get('/api/aulas/', {'tipo': 'LABORATORIO', 'capacidad_min': 30, 'search': 'Lab'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['nombre'], 'Laboratorio')
        self.assertEqual(self.client.get('/api/aulas/', {'capacidad_min': 'abc'}).status_code, 400)

    def test_filtros_de_equipo_y_equipos_por_aula(self):
        Equipamiento.objects.create(nombre='Móvil', cantidad=2, trasladable=True, categoria=self.categoria)
        self.assertEqual(self.client.get('/api/equipamientos/').data['count'], 2)
        response = self.client.get('/api/equipamientos/', {'trasladable': 'false', 'aula': self.aula.pk, 'categoria': self.categoria.pk, 'estado': 'DISPONIBLE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id_equipo'], self.equipo.pk)
        response = self.client.get(f'/api/aulas/{self.aula.pk}/equipamientos/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        for filtro in [{'aula': 'abc'}, {'categoria': -1}, {'trasladable': 'talvez'}, {'estado': 'ROTO'}]:
            self.assertEqual(self.client.get('/api/equipamientos/', filtro).status_code, 400)

    def test_listados_tienen_paginacion(self):
        Aula.objects.bulk_create([Aula(nombre=f'Aula extra {i}', capacidad=10) for i in range(55)])
        response = self.client.get('/api/aulas/')
        self.assertEqual(response.data['count'], 56)
        self.assertEqual(len(response.data['results']), 50)
        self.assertIsNotNone(response.data['next'])
        response = self.client.get('/api/aulas/', {'page': 2})
        self.assertEqual(len(response.data['results']), 6)
