from datetime import date, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.test import APITestCase

from espacios.models import Aula, Categoria, Equipamiento
from usuarios.models import Rol, Usuario
from .models import (
    Actividad, EstadoReserva, Participante, Reserva, ReservaAula,
    ReservaParticipante, SolicitudEquipo,
)
from .services import obtener_aulas_disponibles


class DisponibilidadAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username='coord', rol=Rol.objects.get(nombre=Rol.COORDINACION), numero_documento='100',
        )
        cls.aula = Aula.objects.create(nombre='Aula 1', capacidad=20)
        cls.otra_aula = Aula.objects.create(nombre='Aula 2', capacidad=40)
        cls.fecha = date(2027, 1, 15)
        for estado in EstadoReserva.Estados.values:
            EstadoReserva.objects.get_or_create(estado=estado)

    def setUp(self):
        self.client.force_authenticate(self.usuario)

    def reservar(self, estado='Pendiente', inicio=time(10), fin=time(12), fecha=None):
        actividad = Actividad.objects.create(
            nombre="Práctica",
            tipo=Actividad.Tipo.CURSO,
            responsable=self.usuario,
            fecha_estimada=fecha or self.fecha,
            horario_inicio_estimado=inicio,
            horario_fin_estimado=fin,
            participantes_estimados=10,
            )
        
        reserva = Reserva.objects.create(
            actividad=actividad,
            fecha_reserva=fecha or self.fecha, 
            horario_inicio=inicio,
            horario_fin=fin,
            estado_reserva=EstadoReserva.objects.get(estado=estado),
            )
        
        ReservaAula.objects.create(reserva=reserva, aula=self.aula)
        return reserva

    def disponibles(self, **cambios):
        return self.client.get('/api/aulas-disponibles/', {
            'fecha': self.fecha.isoformat(), 'hora_inicio': '10:00', 'hora_fin': '12:00', **cambios,
        })

    def test_pendientes_y_confirmadas_bloquean_superposiciones(self):
        reserva = self.reservar()
        for estado in ['Pendiente', 'Confirmada']:
            reserva.estado_reserva = EstadoReserva.objects.get(estado=estado)
            reserva.save()
            for inicio, fin in [('09:00', '11:00'), ('11:00', '13:00'), ('10:30', '11:30'), ('09:00', '13:00'), ('10:00', '12:00')]:
                with self.subTest(estado=estado, inicio=inicio, fin=fin):
                    response = self.disponibles(hora_inicio=inicio, hora_fin=fin)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual([a['id'] for a in response.data], [self.otra_aula.pk])

    def test_horarios_consecutivos_no_se_superponen(self):
        self.reservar()
        for inicio, fin in [('08:00', '10:00'), ('12:00', '14:00')]:
            response = self.disponibles(hora_inicio=inicio, hora_fin=fin)
            self.assertEqual(len(response.data), 2)

    def test_canceladas_rechazadas_y_otras_fechas_no_bloquean(self):
        self.reservar(estado='Cancelada')
        self.reservar(estado='Rechazada')
        self.reservar(fecha=date(2027, 1, 16))
        self.assertEqual(len(self.disponibles().data), 2)

    def test_aulas_no_operativas_no_aparecen(self):
        for estado in ['MANTENIMIENTO', 'FUERA_SERVICIO']:
            self.aula.estado = estado
            self.aula.save()
            self.assertEqual([a['id'] for a in self.disponibles().data], [self.otra_aula.pk])

    def test_capacidad_minima_y_contrato_existente(self):
        response = self.disponibles(capacidad_min=30)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{'id': self.otra_aula.pk, 'nombre': 'Aula 2', 'capacidad': 40}])

    def test_parametros_invalidos_devuelven_400(self):
        self.assertEqual(self.client.get('/api/aulas-disponibles/').status_code, 400)
        for cambios in [
            {'fecha': '2027-02-30'}, {'hora_inicio': '25:00'},
            {'hora_inicio': '12:00'}, {'hora_inicio': '13:00'},
            {'hora_inicio': '10:00+03:00'}, {'hora_fin': '12:00Z'},
            {'capacidad_min': 0}, {'capacidad_min': 'abc'},
        ]:
            with self.subTest(cambios=cambios):
                self.assertEqual(self.disponibles(**cambios).status_code, 400)

    def test_servicio_tambien_rechaza_intervalos_invalidos(self):
        with self.assertRaises(ValueError):
            obtener_aulas_disponibles(self.fecha, time(12), time(10))

    def test_aulas_y_equipos_con_reservas_no_se_eliminan_por_api(self):
        self.usuario.rol = Rol.objects.get(nombre=Rol.ADMIN)
        self.usuario.save()
        reserva = self.reservar()
        equipo = Equipamiento.objects.create(
            nombre='Simulador', categoria=Categoria.objects.create(nombre='Simulación'),
            aula=self.otra_aula,
        )
        SolicitudEquipo.objects.create(
            reserva=reserva, equipamiento=equipo, cantidad_solicitada=1, cantidad_critica=1,
        )
        self.assertEqual(self.client.delete(f'/api/aulas/{self.aula.pk}/').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/equipamientos/{equipo.pk}/').status_code, 409)


class ActividadesYParticipantesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.responsable = Usuario.objects.create_user(
            username='responsable', rol=Rol.objects.get(nombre=Rol.COORDINACION),
            numero_documento='800',
        )
        cls.actividad = Actividad.objects.create(
            nombre='Práctica', tipo=Actividad.Tipo.PRACTICA,
            responsable=cls.responsable, fecha_estimada=date(2027, 1, 15),
            horario_inicio_estimado=time(10), horario_fin_estimado=time(12),
            participantes_estimados=10,
        )
        cls.participante = Participante.objects.create(
            nombres='Ana', apellidos='Gomez', tipo_documento='DNI',
            numero_documento='801', fecha_nacimiento=date(2000, 1, 1),
            nacionalidad='Argentina', lugar_residencia='CABA',
            mail='ana@example.com', celular='1100000000',
        )

    def reservar(self):
        return Reserva.objects.create(
            actividad=self.actividad, fecha_reserva=self.actividad.fecha_estimada,
            horario_inicio=time(10), horario_fin=time(12),
        )

    def test_actividad_rechaza_horario_final_igual_o_anterior(self):
        for fin in [time(10), time(9)]:
            with self.subTest(fin=fin):
                self.actividad.horario_fin_estimado = fin
                with self.assertRaises(ValidationError) as error:
                    self.actividad.full_clean()
                self.assertIn('horario_fin_estimado', error.exception.message_dict)

    def test_actividad_requiere_al_menos_un_participante_estimado(self):
        self.actividad.participantes_estimados = 0
        with self.assertRaises(ValidationError) as error:
            self.actividad.full_clean()
        self.assertIn('participantes_estimados', error.exception.message_dict)

    def test_responsable_con_actividades_no_se_elimina(self):
        with self.assertRaises(ProtectedError):
            self.responsable.delete()
        self.assertTrue(Usuario.objects.filter(pk=self.responsable.pk).exists())

    def test_una_persona_tiene_rol_y_asistencia_independientes_por_reserva(self):
        primera = self.reservar()
        segunda = self.reservar()
        ReservaParticipante.objects.create(
            reserva=primera, participante=self.participante, rol='DOCENTE', presente=True,
        )
        ReservaParticipante.objects.create(
            reserva=segunda, participante=self.participante, rol='OBSERVADOR', presente=False,
        )
        self.assertCountEqual(self.participante.reservas.all(), [primera, segunda])
        self.assertCountEqual(
            self.participante.reservas_participantes.values_list('rol', 'presente'),
            [('DOCENTE', True), ('OBSERVADOR', False)],
        )

    def test_no_se_duplica_una_persona_en_la_misma_reserva(self):
        reserva = self.reservar()
        ReservaParticipante.objects.create(reserva=reserva, participante=self.participante)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ReservaParticipante.objects.create(reserva=reserva, participante=self.participante)
        self.assertEqual(reserva.participantes.count(), 1)

    def test_eliminar_una_reserva_conserva_la_persona_y_sus_otras_reservas(self):
        primera = self.reservar()
        segunda = self.reservar()
        for reserva in [primera, segunda]:
            ReservaParticipante.objects.create(reserva=reserva, participante=self.participante)
        primera.delete()
        self.assertTrue(Participante.objects.filter(pk=self.participante.pk).exists())
        self.assertEqual(list(self.participante.reservas.all()), [segunda])
