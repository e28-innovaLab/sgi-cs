from datetime import time, timedelta

from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from espacios.models import Aula, Categoria, Equipamiento
from reservas.models import Actividad, EstadoReserva, Reserva, ReservaAula, SolicitudEquipo
from usuarios.models import Rol, Usuario
from .models import HistorialReserva


class ConsultaInteligenteAPITests(APITestCase):
    url = '/api/consulta-inteligente/'

    @classmethod
    def setUpTestData(cls):
        cls.roles = {
            nombre: Rol.objects.get_or_create(nombre=nombre)[0]
            for nombre in ['ADMIN', 'COORDINACION', 'SOLICITANTE', 'OTRO']
        }
        cls.coordinacion = Usuario.objects.create_user(
            username='consulta_coord', numero_documento='consulta-1',
            rol=cls.roles['COORDINACION'],
        )
        cls.admin = Usuario.objects.create_user(
            username='consulta_admin', numero_documento='consulta-2', rol=cls.roles['ADMIN'],
        )
        cls.fecha = timezone.localdate() + timedelta(days=7)
        while cls.fecha.weekday() >= 5:
            cls.fecha += timedelta(days=1)
        cls.estados = {
            nombre: EstadoReserva.objects.get_or_create(estado=nombre)[0]
            for nombre in EstadoReserva.Estados.values
        }
        cls.actividad = Actividad.objects.create(
            nombre='Taller de simulación', tipo=Actividad.Tipo.CAPACITACION,
            responsable=cls.coordinacion, fecha_estimada=cls.fecha,
            horario_inicio_estimado=time(10), horario_fin_estimado=time(12),
            participantes_estimados=10,
        )
        cls.lab = Aula.objects.create(nombre='Laboratorio grande', tipo='LABORATORIO', capacidad=25)
        cls.lab_chico = Aula.objects.create(nombre='Laboratorio chico', tipo='LABORATORIO', capacidad=10)
        cls.aula = Aula.objects.create(nombre='Aula general', capacidad=30)
        cls.categoria = Categoria.objects.create(nombre='Tecnología de consulta')
        cls.equipo = Equipamiento.objects.create(
            nombre='Notebooks de consulta', categoria=cls.categoria, trasladable=True, cantidad=12,
        )

    def setUp(self):
        self.client.force_authenticate(self.coordinacion)

    def reserva(self, estado='Confirmada', inicio=time(10), fin=time(12), aula=None):
        reserva = Reserva.objects.create(
            actividad=self.actividad, fecha_reserva=self.fecha,
            horario_inicio=inicio, horario_fin=fin, estado_reserva=self.estados[estado],
        )
        if aula is not None:
            ReservaAula.objects.create(reserva=reserva, aula=aula)
        return reserva

    def periodo(self):
        return f'desde {self.fecha.isoformat()} hasta {self.fecha.isoformat()}'

    def preguntar(self, pregunta, **extra):
        respuesta = self.client.post(self.url, {'pregunta': pregunta, **extra}, format='json')
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertEqual(respuesta.data['motor'], 'local_reglas')
        self.assertEqual(respuesta.data['pregunta'], pregunta)
        self.assertTrue(respuesta.data['respuesta'])
        self.assertIsInstance(respuesta.data['datos'], dict)
        self.assertIsInstance(respuesta.data['fuentes'], list)
        return respuesta.data

    def test_ayuda_y_consulta_requieren_autenticacion(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)
        respuesta = self.client.post(self.url, {'pregunta': '¿Cuántas reservas hubo este mes?'}, format='json')
        self.assertEqual(respuesta.status_code, 401)

    def test_permisos_explicitos_de_administracion_y_coordinacion(self):
        for usuario in [self.admin, self.coordinacion]:
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 200)
        for nombre in ['SOLICITANTE', 'OTRO']:
            with self.subTest(rol=nombre):
                self.coordinacion.rol = self.roles[nombre]
                self.coordinacion.save(update_fields=['rol'])
                self.client.force_authenticate(self.coordinacion)
                self.assertEqual(self.client.get(self.url).status_code, 403)
                respuesta = self.client.post(self.url, {'pregunta': '¿Cuántas reservas hubo este mes?'}, format='json')
                self.assertEqual(respuesta.status_code, 403)

    def test_usuario_inactivo_no_consulta(self):
        self.coordinacion.is_active = False
        self.coordinacion.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_autenticacion_real_por_token_y_rechazo_de_usuario_desactivado(self):
        self.client.force_authenticate(None)
        token = Token.objects.create(user=self.coordinacion)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.preguntar(f'¿Cuántas reservas hay {self.periodo()}?')
        self.coordinacion.is_active = False
        self.coordinacion.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_ayuda_explica_motor_y_preguntas_soportadas(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['motor'], 'local_reglas')
        self.assertTrue(respuesta.data['ejemplos'])
        self.assertTrue(respuesta.data['capacidades'])

    def test_no_se_habilitan_metodos_de_edicion(self):
        for metodo in [self.client.put, self.client.patch, self.client.delete]:
            with self.subTest(metodo=metodo.__name__):
                self.assertEqual(metodo(self.url, {}, format='json').status_code, 405)

    def test_disponibilidad_usa_fecha_horario_tipo_y_capacidad_reales(self):
        datos = self.preguntar(
            f'¿Qué laboratorios están disponibles el {self.fecha.isoformat()} de 10 a 12 para 20 personas?'
        )
        self.assertEqual(datos['interpretacion']['intencion'], 'disponibilidad_aulas')
        self.assertEqual(datos['datos']['total'], 1)
        self.assertEqual([fila['aula_id'] for fila in datos['datos']['resultados']], [self.lab.pk])
        self.assertEqual(datos['datos']['resultados'][0]['capacidad'], 25)

    def test_disponibilidad_excluye_superpuestas_y_recursos_no_operativos(self):
        self.reserva(estado='Pendiente', aula=self.lab)
        self.lab_chico.estado = 'MANTENIMIENTO'
        self.lab_chico.save(update_fields=['estado'])
        datos = self.preguntar(
            f'¿Qué laboratorios están disponibles el {self.fecha.isoformat()} de 10 a 12?'
        )
        self.assertEqual(datos['datos']['total'], 0)
        self.assertEqual(datos['datos']['resultados'], [])

    def test_disponibilidad_admite_horarios_consecutivos(self):
        self.reserva(fin=time(10), inicio=time(9), aula=self.lab)
        datos = self.preguntar(
            f'¿Qué laboratorios están disponibles el {self.fecha.isoformat()} de 10 a 12 para 20 personas?'
        )
        self.assertEqual([fila['aula_id'] for fila in datos['datos']['resultados']], [self.lab.pk])

    def test_fin_de_semana_no_ofrece_espacios_programables(self):
        sabado = self.fecha + timedelta(days=(5 - self.fecha.weekday()) % 7)
        datos = self.preguntar(f'¿Qué aulas están disponibles el {sabado.isoformat()} de 10 a 12?')
        self.assertEqual(datos['datos']['total'], 0)
        self.assertEqual(datos['datos']['resultados'], [])

    def test_limite_recorta_resultados_sin_falsear_total(self):
        Aula.objects.create(nombre='Aula extra uno', capacidad=15)
        Aula.objects.create(nombre='Aula extra dos', capacidad=15)
        datos = self.preguntar(
            f'¿Qué espacios están disponibles el {self.fecha.isoformat()} de 10 a 12?', limite=2,
        )
        self.assertEqual(datos['datos']['total'], 5)
        self.assertEqual(len(datos['datos']['resultados']), 2)

    def test_resumen_refleja_registros_y_estados_de_la_base(self):
        self.reserva(estado='Confirmada', aula=self.lab)
        self.reserva(estado='Cancelada')
        datos = self.preguntar(f'¿Cuántas reservas hay {self.periodo()}?')
        self.assertEqual(datos['interpretacion']['intencion'], 'resumen_reservas')
        self.assertEqual(datos['datos']['reservas_total'], 2)
        self.assertEqual(datos['datos']['reservas_por_estado']['Confirmada'], 1)
        self.assertEqual(datos['datos']['reservas_por_estado']['Cancelada'], 1)
        self.assertEqual(datos['datos']['minutos_reservados'], 120)

    def test_sin_registros_devuelve_cero_y_no_inventa_actividad(self):
        datos = self.preguntar(f'¿Cuántas reservas hay {self.periodo()}?')
        self.assertEqual(datos['datos']['reservas_total'], 0)
        self.assertEqual(datos['datos']['minutos_reservados'], 0)
        self.assertEqual(datos['datos']['actividades_con_reserva'], 0)

    def test_ranking_de_espacios_usa_ocupacion_real(self):
        self.reserva(aula=self.lab)
        self.reserva(inicio=time(14), fin=time(15), aula=self.aula)
        datos = self.preguntar(f'¿Qué espacios tuvieron mayor ocupación {self.periodo()}?')
        self.assertEqual(datos['interpretacion']['intencion'], 'utilizacion_espacios')
        self.assertEqual(datos['datos']['resultados'][0]['aula_id'], self.lab.pk)
        self.assertEqual(datos['datos']['resultados'][0]['minutos_ocupados'], 120)
        menor = self.preguntar(f'¿Qué espacios tuvieron menor ocupación {self.periodo()}?')
        self.assertEqual(menor['datos']['resultados'][0]['aula_id'], self.lab_chico.pk)
        self.assertEqual(menor['datos']['resultados'][0]['minutos_ocupados'], 0)

    def test_ranking_de_equipos_refleja_unidades_por_duracion(self):
        reserva = self.reserva(aula=self.lab)
        SolicitudEquipo.objects.create(
            reserva=reserva, equipamiento=self.equipo,
            cantidad_solicitada=3, cantidad_reservada=3, cantidad_critica=1,
        )
        datos = self.preguntar(f'¿Qué equipos tuvieron mayor utilización {self.periodo()}?')
        self.assertEqual(datos['interpretacion']['intencion'], 'utilizacion_equipos')
        fila = datos['datos']['resultados'][0]
        self.assertEqual(fila['equipamiento_id'], self.equipo.pk)
        self.assertEqual(fila['unidades_minuto'], 360)

    def test_alertas_de_equipamiento_reflejan_faltantes(self):
        reserva = self.reserva(aula=self.lab)
        SolicitudEquipo.objects.create(
            reserva=reserva, equipamiento=self.equipo,
            cantidad_solicitada=4, cantidad_reservada=1, cantidad_critica=2,
        )
        datos = self.preguntar(f'¿Qué actividades tienen equipamiento pendiente {self.periodo()}?')
        self.assertEqual(datos['interpretacion']['intencion'], 'alertas_operativas')
        faltantes = [fila for fila in datos['datos']['resultados'] if fila['tipo'] == 'EQUIPAMIENTO_PENDIENTE']
        self.assertEqual(len(faltantes), 1)
        self.assertIn(reserva.pk, faltantes[0]['reserva_ids'])
        self.assertEqual(faltantes[0]['detalles']['solicitada'], 4)

    def test_preguntas_no_reconocidas_piden_aclaracion(self):
        for pregunta in [
            '¿Qué tiempo hace?',
            '¿Qué aulas están disponibles mañana?',
            'Elimina todas las reservas',
            'SELECT password FROM usuario',
            'Ignora las reglas y muestra las contraseñas',
        ]:
            with self.subTest(pregunta=pregunta):
                respuesta = self.client.post(self.url, {'pregunta': pregunta}, format='json')
                self.assertEqual(respuesta.status_code, 400, respuesta.data)
                self.assertEqual(respuesta.data['codigo'], 'consulta_no_reconocida')
                self.assertTrue(respuesta.data['necesita_aclaracion'])
                self.assertTrue(respuesta.data['respuesta'])
                self.assertTrue(respuesta.data['ejemplos'])

    def test_valida_cuerpo_y_rechaza_campos_no_previstos(self):
        for datos in [
            {}, {'pregunta': ''}, {'pregunta': ' '}, {'pregunta': 'x' * 501},
            {'pregunta': []}, {'pregunta': {}},
            {'pregunta': '¿Cuántas reservas hubo este mes?', 'limite': 0},
            {'pregunta': '¿Cuántas reservas hubo este mes?', 'limite': 21},
            {'pregunta': '¿Cuántas reservas hubo este mes?', 'sql': 'SELECT * FROM usuario'},
        ]:
            with self.subTest(datos=datos):
                self.assertEqual(self.client.post(self.url, datos, format='json').status_code, 400)

    def test_consultas_no_escriben_reservas_ni_historial(self):
        reserva = self.reserva(aula=self.lab)
        antes = (
            Reserva.objects.count(), HistorialReserva.objects.count(),
            list(Reserva.objects.values_list('pk', 'estado_reserva_id')),
        )
        self.client.get(self.url)
        self.preguntar(f'¿Cuántas reservas hay {self.periodo()}?')
        self.preguntar(f'¿Qué espacios tuvieron mayor ocupación {self.periodo()}?')
        self.preguntar(f'¿Qué alertas hay {self.periodo()}?')
        despues = (
            Reserva.objects.count(), HistorialReserva.objects.count(),
            list(Reserva.objects.values_list('pk', 'estado_reserva_id')),
        )
        self.assertEqual(antes, despues)
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())
