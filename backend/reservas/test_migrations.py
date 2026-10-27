"""Comprueba la actualización de una base con participantes ya cargados."""

from datetime import date, time

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionParticipantesTests(TransactionTestCase):
    origen = [('reservas', '0005_crear_actividad')]
    destino = [('reservas', '0006_remove_participante_presente_and_more')]

    def setUp(self):
        super().setUp()
        self.addCleanup(self.restaurar_migraciones)
        executor = MigrationExecutor(connection)
        executor.migrate(self.origen)
        self.apps_anteriores = executor.loader.project_state(self.origen).apps

    def restaurar_migraciones(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def migrar(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.destino)
        return executor.loader.project_state(self.destino).apps

    def crear_participantes(self):
        Rol = self.apps_anteriores.get_model('usuarios', 'Rol')
        Usuario = self.apps_anteriores.get_model('usuarios', 'Usuario')
        Actividad = self.apps_anteriores.get_model('reservas', 'Actividad')
        Reserva = self.apps_anteriores.get_model('reservas', 'Reserva')
        Participante = self.apps_anteriores.get_model('reservas', 'Participante')
        rol, _ = Rol.objects.get_or_create(nombre='COORDINACION')
        usuario = Usuario.objects.create(
            username='responsable', rol=rol, numero_documento='900',
        )
        actividad = Actividad.objects.create(
            nombre='Práctica', tipo='PRACTICA', responsable=usuario,
            fecha_estimada=date(2027, 1, 15),
            horario_inicio_estimado=time(10), horario_fin_estimado=time(12),
            participantes_estimados=3,
        )
        esperados = []
        for indice, presente in enumerate([True, False, None]):
            reserva = Reserva.objects.create(
                actividad=actividad, fecha_reserva=date(2027, 1, 15),
                horario_inicio=time(10 + indice), horario_fin=time(11 + indice),
            )
            participante = Participante.objects.create(
                reserva=reserva, presente=presente,
                nombres=f'Persona {indice}', apellidos='Prueba',
                tipo_documento='DNI', numero_documento=str(1000 + indice),
                fecha_nacimiento=date(2000, 1, 1), nacionalidad='Argentina',
                lugar_residencia='CABA', mail=f'persona{indice}@example.com',
                celular='1100000000',
            )
            esperados.append((reserva.pk, participante.pk, presente, 'OTRO'))
        return esperados

    def test_conserva_reserva_y_asistencia_de_cada_participante(self):
        esperados = self.crear_participantes()
        apps = self.migrar()
        Vinculo = apps.get_model('reservas', 'ReservaParticipante')
        ParticipanteNuevo = apps.get_model('reservas', 'Participante')
        self.assertCountEqual(
            Vinculo.objects.values_list('reserva_id', 'participante_id', 'presente', 'rol'),
            esperados,
        )
        self.assertEqual(ParticipanteNuevo.objects.count(), 3)

    def test_reversion_restaura_vinculos_y_asistencia_si_hay_una_reserva_por_persona(self):
        esperados = self.crear_participantes()
        self.migrar()
        executor = MigrationExecutor(connection)
        executor.migrate(self.origen)
        Participante = executor.loader.project_state(self.origen).apps.get_model(
            'reservas', 'Participante',
        )
        self.assertCountEqual(
            Participante.objects.values_list('reserva_id', 'pk', 'presente'),
            [valores[:3] for valores in esperados],
        )

    def test_reversion_rechaza_participantes_con_multiples_reservas(self):
        esperados = self.crear_participantes()
        apps = self.migrar()
        Vinculo = apps.get_model('reservas', 'ReservaParticipante')
        Vinculo.objects.create(
            reserva_id=esperados[1][0], participante_id=esperados[0][1], rol='DOCENTE',
        )
        with self.assertRaisesMessage(RuntimeError, 'exactamente una reserva'):
            MigrationExecutor(connection).migrate(self.origen)
        self.assertEqual(Vinculo.objects.count(), 4)

    def test_admite_una_base_sin_participantes(self):
        apps = self.migrar()
        self.assertFalse(apps.get_model('reservas', 'ReservaParticipante').objects.exists())
