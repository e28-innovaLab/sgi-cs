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
from .services import (
    obtener_aulas_disponibles,
    solicitar_equipamiento_reserva,
    actualizar_solicitud_equipamiento,
    confirmar_reserva,
    rechazar_reserva,
    cancelar_reserva,
    finalizar_reservas_vencidas,
)


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
            nombre="PrÃ¡ctica",
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

    def crear_equipamiento(self, nombre="Proyector", cantidad=5):
        categoria = Categoria.objects.create(
            nombre=f"Categoría {nombre}"
        )

        return Equipamiento.objects.create(
            nombre=nombre,
            categoria=categoria,
            cantidad=cantidad,
            estado=Equipamiento.Estado.DISPONIBLE,
            trasladable=True,
        )

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
        self.reservar(fecha=date(2027, 1, 18))
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
            nombre='Simulador', categoria=Categoria.objects.create(nombre='SimulaciÃ³n'),
            aula=self.otra_aula,
        )
        SolicitudEquipo.objects.create(
            reserva=reserva, equipamiento=equipo, cantidad_solicitada=1, cantidad_critica=1,
        )
        self.assertEqual(self.client.delete(f'/api/aulas/{self.aula.pk}/').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/equipamientos/{equipo.pk}/').status_code, 409)


    def test_estados_terminales_no_pueden_cambiarse(self):
        estados_terminales = [
            'Cancelada',
            'Rechazada',
            'Finalizada',
        ]

        estado_nuevo = EstadoReserva.objects.get(
            estado='Confirmada'
        )

        for estado in estados_terminales:
            with self.subTest(estado=estado):
                reserva = self.reservar(estado=estado)

                reserva.estado_reserva = estado_nuevo

                with self.assertRaises(ValidationError):
                    reserva.save()

                reserva.refresh_from_db()

                self.assertEqual(
                    reserva.estado_reserva.estado,
                    estado,
                )

    def test_estado_terminal_puede_guardarse_sin_cambiarlo(self):
        reserva = self.reservar(estado='Cancelada')

        reserva.detalle = 'ModificaciÃ³n administrativa'

        reserva.save()

        reserva.refresh_from_db()

        self.assertEqual(
            reserva.estado_reserva.estado,
            'Cancelada',
        )
        self.assertEqual(
            reserva.detalle,
            'ModificaciÃ³n administrativa',
        )


    def test_servicios_no_modifican_estados_terminales(self):
        estados_terminales = [
            'Cancelada',
            'Rechazada',
            'Finalizada',
        ]

        operaciones = [
            confirmar_reserva,
            rechazar_reserva,
            cancelar_reserva,
        ]

        for estado in estados_terminales:
            reserva = self.reservar(estado=estado)

            for operacion in operaciones:
                with self.subTest(
                    estado=estado,
                    operacion=operacion.__name__,
                ):
                    with self.assertRaises(ValidationError):
                        operacion(reserva.pk, self.usuario)

            reserva.refresh_from_db()

            self.assertEqual(
                reserva.estado_reserva.estado,
                estado,
            )

    def test_finalizacion_automatica_respeta_estados_terminales(self):
        estados_terminales = [
            'Cancelada',
            'Rechazada',
            'Finalizada',
        ]

        reservas = []

        for estado in estados_terminales:
            reservas.append(self.reservar(estado=estado))

        resultado = finalizar_reservas_vencidas()

        self.assertEqual(resultado, {
            'canceladas': 0,
            'finalizadas': 0,
        })

        for reserva in reservas:
            reserva.refresh_from_db()

            self.assertIn(
                reserva.estado_reserva.estado,
                estados_terminales,
            )


    def test_solicitar_equipamiento_reserva_toda_la_cantidad_disponible(self):
        reserva = self.reservar()
        equipo = self.crear_equipamiento(
            nombre="Proyector",
            cantidad=5,
        )

        solicitud = solicitar_equipamiento_reserva(
            reserva_id=reserva.pk,
            equipamiento_id=equipo.pk,
            cantidad_solicitada=5,
            cantidad_critica=2,
        )

        self.assertEqual(solicitud.cantidad_solicitada, 5)
        self.assertEqual(solicitud.cantidad_reservada, 5)
        self.assertEqual(solicitud.cantidad_critica, 2)
        self.assertFalse(solicitud.asignacion_automatica)


    def test_solicitar_equipamiento_permite_asignacion_parcial(self):
        # Creamos dos reservas que se superponen.
        reserva_existente = self.reservar()
        reserva_nueva = self.reservar()

        equipo = self.crear_equipamiento(
            nombre="Proyector",
            cantidad=5,
        )

        # La primera reserva ya tiene comprometidas 3 unidades.
        SolicitudEquipo.objects.create(
            reserva=reserva_existente,
            equipamiento=equipo,
            cantidad_solicitada=3,
            cantidad_reservada=3,
            cantidad_critica=1,
        )

        # La segunda reserva solicita 4 unidades.
        solicitud = solicitar_equipamiento_reserva(
            reserva_id=reserva_nueva.pk,
            equipamiento_id=equipo.pk,
            cantidad_solicitada=4,
            cantidad_critica=2,
        )

        # Solo quedan 2 unidades disponibles.
        self.assertEqual(solicitud.cantidad_solicitada, 4)
        self.assertEqual(solicitud.cantidad_reservada, 2)
        self.assertEqual(solicitud.cantidad_critica, 2)


    def test_solicitar_equipamiento_rechaza_solicitud_sin_stock(self):
        reserva_existente = self.reservar()
        reserva_nueva = self.reservar()

        equipo = self.crear_equipamiento(
            nombre="Proyector",
            cantidad=5,
        )

        # La primera reserva consume todo el stock.
        SolicitudEquipo.objects.create(
            reserva=reserva_existente,
            equipamiento=equipo,
            cantidad_solicitada=5,
            cantidad_reservada=5,
            cantidad_critica=2,
        )

        # La segunda reserva no puede obtener unidades.
        with self.assertRaisesMessage(
            ValidationError,
            "No hay unidades disponibles de este equipamiento.",
        ):
            solicitar_equipamiento_reserva(
                reserva_id=reserva_nueva.pk,
                equipamiento_id=equipo.pk,
                cantidad_solicitada=2,
                cantidad_critica=1,
            )

        # Comprobamos que no se haya creado una solicitud.
        self.assertFalse(
            SolicitudEquipo.objects.filter(
                reserva=reserva_nueva,
                equipamiento=equipo,
            ).exists()
        )


    def test_actualizar_solicitud_sin_stock_conserva_solicitud_original(self):
        reserva_existente = self.reservar()
        reserva_actual = self.reservar()

        equipo_original = self.crear_equipamiento(
            nombre="Proyector original",
            cantidad=3,
        )

        equipo_nuevo = self.crear_equipamiento(
            nombre="Proyector nuevo",
            cantidad=5,
        )

        # Creamos una solicitud manual para la reserva actual.
        solicitud_original = SolicitudEquipo.objects.create(
            reserva=reserva_actual,
            equipamiento=equipo_original,
            cantidad_solicitada=2,
            cantidad_reservada=2,
            cantidad_critica=1,
            asignacion_automatica=False,
        )

        # Otra reserva consume todo el stock del nuevo equipo.
        SolicitudEquipo.objects.create(
            reserva=reserva_existente,
            equipamiento=equipo_nuevo,
            cantidad_solicitada=5,
            cantidad_reservada=5,
            cantidad_critica=2,
        )

        # Intentamos cambiar al equipo sin stock.
        with self.assertRaisesMessage(
            ValidationError,
            "No hay unidades disponibles de este equipamiento.",
        ):
            actualizar_solicitud_equipamiento(
                solicitud_id=solicitud_original.pk,
                equipamiento_id=equipo_nuevo.pk,
                cantidad_solicitada=3,
                cantidad_critica=2,
            )

        # Recuperamos la solicitud original desde la base de datos.
        solicitud_original.refresh_from_db()

        # Comprobamos que no haya sufrido modificaciones.
        self.assertEqual(
            solicitud_original.equipamiento_id,
            equipo_original.pk,
        )
        self.assertEqual(solicitud_original.cantidad_solicitada, 2)
        self.assertEqual(solicitud_original.cantidad_reservada, 2)
        self.assertEqual(solicitud_original.cantidad_critica, 1)

        self.assertTrue(
            SolicitudEquipo.objects.filter(
                pk=solicitud_original.pk
            ).exists()
        )


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
            creado_por=cls.responsable, nombres='Ana', apellidos='Gomez', tipo_documento='DNI',
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
