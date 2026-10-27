from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Rol, Usuario


class UsuariosAPITests(APITestCase):
    password = 'PruebaSegura!4729'

    @classmethod
    def setUpTestData(cls):
        cls.rol_admin = Rol.objects.get(nombre=Rol.ADMIN)
        cls.rol_coordinacion = Rol.objects.get(nombre=Rol.COORDINACION)
        cls.admin = Usuario.objects.create_user(
            username='admin', password=cls.password, rol=cls.rol_admin,
            numero_documento='100',
        )
        cls.coordinacion = Usuario.objects.create_user(
            username='coord', password=cls.password, rol=cls.rol_coordinacion,
            numero_documento='101',
        )

    def setUp(self):
        cache.clear()

    def autenticar(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return token.key

    def datos_usuario(self, **cambios):
        return {
            'username': 'nuevo', 'first_name': 'Ana', 'last_name': 'Gomez',
            'email': 'ana@example.com', 'tipo_documento': 'DNI',
            'numero_documento': '102', 'rol': self.rol_coordinacion.pk,
            'password': self.password, **cambios,
        }

    def test_login_entrega_token_perfil_y_registra_ingreso(self):
        response = self.client.post('/api/auth/login/', {'username': 'coord', 'password': self.password})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Token.objects.filter(key=response.data['token'], user=self.coordinacion).exists())
        self.assertEqual(response.data['usuario']['rol']['nombre'], Rol.COORDINACION)
        self.assertNotIn('password', response.data['usuario'])
        self.coordinacion.refresh_from_db()
        self.assertIsNotNone(self.coordinacion.last_login)

    def test_login_rechaza_credenciales_incorrectas_e_inactivos(self):
        self.coordinacion.is_active = False
        self.coordinacion.save()
        for username, password in [('admin', 'incorrecta'), ('coord', self.password), ('inexistente', self.password)]:
            with self.subTest(username=username):
                response = self.client.post('/api/auth/login/', {'username': username, 'password': password})
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Token.objects.exists())

    def test_login_limita_intentos(self):
        datos = {'username': 'admin', 'password': 'incorrecta'}
        for _ in range(10):
            self.assertEqual(self.client.post('/api/auth/login/', datos).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/login/', datos).status_code, 429)

    def test_api_requiere_token_valido(self):
        for url in ['/api/auth/me/', '/api/usuarios/', '/api/roles/', '/api/aulas/', '/api/equipamientos/', '/api/aulas-disponibles/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Token inexistente')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)

    def test_logout_revoca_token(self):
        self.autenticar(self.coordinacion)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 204)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.assertFalse(Token.objects.filter(user=self.coordinacion).exists())

    def test_coordinacion_no_administra_usuarios(self):
        self.autenticar(self.coordinacion)
        self.assertEqual(self.client.get('/api/usuarios/').status_code, 403)
        self.assertEqual(self.client.post('/api/usuarios/', self.datos_usuario()).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/usuarios/{self.admin.pk}/', {'rol': self.rol_admin.pk}).status_code, 403)
        self.assertEqual(self.client.get('/api/roles/').status_code, 200)

    def test_admin_crea_usuario_con_hash_de_password(self):
        self.autenticar(self.admin)
        response = self.client.post('/api/usuarios/', self.datos_usuario())
        self.assertEqual(response.status_code, 201, response.data)
        usuario = Usuario.objects.get(pk=response.data['id_usuario'])
        self.assertTrue(usuario.check_password(self.password))
        self.assertNotEqual(usuario.password, self.password)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.is_active)
        self.assertNotIn('password', response.data)
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'nuevo', 'password': self.password}).status_code, 200)

    def test_password_obligatoria_y_validacion_de_seguridad(self):
        self.autenticar(self.admin)
        datos = self.datos_usuario()
        datos.pop('password')
        self.assertEqual(self.client.post('/api/usuarios/', datos).status_code, 400)
        for password in ['123', '', 'password']:
            with self.subTest(password=password):
                response = self.client.post('/api/usuarios/', self.datos_usuario(password=password))
                self.assertEqual(response.status_code, 400)
                self.assertIn('password', response.data)
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_duplicados_y_rol_inexistente_son_errores_de_validacion(self):
        self.autenticar(self.admin)
        for cambios in [{'username': 'admin'}, {'numero_documento': '100'}, {'rol': 99999}]:
            with self.subTest(cambios=cambios):
                self.assertEqual(self.client.post('/api/usuarios/', self.datos_usuario(**cambios)).status_code, 400)

    def test_no_es_posible_elevar_privilegios_django_por_api(self):
        self.autenticar(self.admin)
        response = self.client.patch(
            f'/api/usuarios/{self.coordinacion.pk}/',
            {'is_staff': True, 'is_superuser': True},
        )
        self.assertEqual(response.status_code, 200)
        self.coordinacion.refresh_from_db()
        self.assertFalse(self.coordinacion.is_staff)
        self.assertFalse(self.coordinacion.is_superuser)

    def test_cambiar_password_revoca_token_anterior(self):
        token_anterior = Token.objects.create(user=self.coordinacion).key
        self.autenticar(self.admin)
        response = self.client.patch(
            f'/api/usuarios/{self.coordinacion.pk}/', {'password': 'OtraClaveSegura!8822'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token_anterior).exists())
        self.coordinacion.refresh_from_db()
        self.assertTrue(self.coordinacion.check_password('OtraClaveSegura!8822'))
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'coord', 'password': self.password}).status_code, 400)

    def test_desactivacion_revoca_token_y_no_borra_historial(self):
        token_anterior = Token.objects.create(user=self.coordinacion).key
        self.autenticar(self.admin)
        response = self.client.patch(f'/api/usuarios/{self.coordinacion.pk}/', {'is_active': False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token_anterior).exists())
        self.assertTrue(Usuario.objects.filter(pk=self.coordinacion.pk, is_active=False).exists())
        self.assertEqual(self.client.delete(f'/api/usuarios/{self.coordinacion.pk}/').status_code, 405)

    def test_editar_usuario_inactivo_no_lo_reactiva_si_se_omite_is_active(self):
        self.coordinacion.is_active = False
        self.coordinacion.save(update_fields=['is_active'])
        self.autenticar(self.admin)
        datos = self.datos_usuario(
            username=self.coordinacion.username,
            numero_documento=self.coordinacion.numero_documento,
        )
        datos.pop('password')
        for metodo in [self.client.patch, self.client.put]:
            with self.subTest(metodo=metodo.__name__):
                response = metodo(f'/api/usuarios/{self.coordinacion.pk}/', datos)
                self.assertEqual(response.status_code, 200, response.data)
                self.coordinacion.refresh_from_db()
                self.assertFalse(self.coordinacion.is_active)

    def test_admin_puede_crear_un_usuario_inactivo_explicitamente(self):
        self.autenticar(self.admin)
        response = self.client.post('/api/usuarios/', self.datos_usuario(is_active=False))
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Usuario.objects.get(pk=response.data['id_usuario']).is_active)

    def test_admin_no_puede_desactivarse_ni_quitarse_su_rol(self):
        self.autenticar(self.admin)
        for cambios in [{'is_active': False}, {'rol': self.rol_coordinacion.pk}]:
            self.assertEqual(self.client.patch(f'/api/usuarios/{self.admin.pk}/', cambios).status_code, 400)

    def test_superusuario_se_crea_con_rol_admin_y_no_es_modificable_por_admin_comun(self):
        superusuario = Usuario.objects.create_superuser(
            username='super', password=self.password, numero_documento='103',
        )
        self.assertEqual(superusuario.rol, self.rol_admin)
        self.autenticar(self.admin)
        self.assertEqual(self.client.patch(f'/api/usuarios/{superusuario.pk}/', {'is_active': False}).status_code, 403)

    def test_rol_desconocido_no_puede_ingresar_ni_usar_token_previo(self):
        self.coordinacion.rol = Rol.objects.create(nombre='OTRO')
        self.coordinacion.save()
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'coord', 'password': self.password}).status_code, 400)
        self.autenticar(self.coordinacion)
        self.assertEqual(self.client.get('/api/aulas/').status_code, 403)

    def test_roles_no_se_modifican_por_api(self):
        self.autenticar(self.admin)
        self.assertEqual(self.client.post('/api/roles/', {'nombre': 'OTRO'}).status_code, 405)
        self.assertEqual(self.client.patch(f'/api/roles/{self.rol_coordinacion.pk}/', {'nombre': 'ADMIN'}).status_code, 405)
