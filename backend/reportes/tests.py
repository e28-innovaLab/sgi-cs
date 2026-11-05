from datetime import time, timedelta
from io import StringIO

from django.core.management import call_command
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from espacios.models import Aula, Categoria, Equipamiento
from reservas.models import (
    Actividad, EstadoReserva, Reserva, ReservaAula, ReservaParticipante, Participante,
    SolicitudEquipo,
)
from reservas.services import asignar_aulas_reserva
from usuarios.models import Rol, Usuario
from .history import registrar_reserva
from .models import HistorialReserva


class ReportesTests(APITestCase):
    urls = [
        '/api/indicadores/resumen/', '/api/indicadores/espacios/',
        '/api/indicadores/equipamiento/', '/api/alertas/',
        '/api/historial/reservas/', '/api/historial/utilizacion/',
    ]

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            username='reportes', numero_documento='9900',
            rol=Rol.objects.get(nombre=Rol.COORDINACION),
        )
        cls.fecha = timezone.localdate() + timedelta(days=10)
        cls.estados = {s: EstadoReserva.objects.get_or_create(estado=s)[0] for s in EstadoReserva.Estados.values}
        cls.actividad = Actividad.objects.create(
            nombre='Práctica', tipo=Actividad.Tipo.PRACTICA, responsable=cls.usuario,
            fecha_estimada=cls.fecha, horario_inicio_estimado=time(10),
            horario_fin_estimado=time(12), participantes_estimados=10,
        )
        cls.aula = Aula.objects.create(nombre='Laboratorio', capacidad=20)
        cls.otra = Aula.objects.create(nombre='Sin uso', capacidad=30)
        cls.equipo = Equipamiento.objects.create(
            nombre='Notebooks', cantidad=10, trasladable=True,
            categoria=Categoria.objects.create(nombre='Tecnología'),
        )

    def setUp(self):
        self.client.force_authenticate(self.usuario)
        self.filtros = {'desde': self.fecha.isoformat(), 'hasta': self.fecha.isoformat()}

    def reserva(self, estado='Confirmada', inicio=time(10), fin=time(12), aulas=None, actividad=None):
        reserva = Reserva.objects.create(
            actividad=actividad or self.actividad, estado_reserva=self.estados.get(estado),
            fecha_reserva=self.fecha, horario_inicio=inicio, horario_fin=fin,
        )
        for aula in (aulas if aulas is not None else [self.aula]):
            ReservaAula.objects.create(reserva=reserva, aula=aula)
        return reserva

    def solicitar(self, reserva, cantidad=3, reservada=3, critica=1, equipo=None):
        return SolicitudEquipo.objects.create(
            reserva=reserva, equipamiento=equipo or self.equipo,
            cantidad_solicitada=cantidad, cantidad_reservada=reservada, cantidad_critica=critica,
        )

    def consultar(self, url, **filtros):
        response = self.client.get(url, {**self.filtros, **filtros})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def alertas(self, **filtros):
        return self.consultar('/api/alertas/', **filtros)['results']

    def test_permisos_y_solo_lectura_en_todos_los_endpoints(self):
        for url in self.urls:
            with self.subTest(url=url):
                self.client.force_authenticate(None)
                self.assertEqual(self.client.get(url).status_code, 401)
                self.client.force_authenticate(self.usuario)
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(self.client.post(url, {}).status_code, 405)
        self.usuario.rol = Rol.objects.create(nombre='OTRO')
        self.usuario.save()
        for url in self.urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.usuario.rol = Rol.objects.get(nombre=Rol.ADMIN)
        self.usuario.save()
        self.assertEqual(self.client.get(self.urls[0]).status_code, 200)
        self.usuario.is_active = False
        self.usuario.save()
        self.assertEqual(self.client.get(self.urls[0]).status_code, 403)

    def test_filtros_invalidos_y_periodos_acotados(self):
        for cambio in [
            {'desde': '2026-02-30'}, {'desde': 'no-fecha'}, {'hasta': '2000-01-01'},
            {'hasta': (self.fecha + timedelta(days=366)).isoformat()},
            {'aula': -1}, {'equipamiento': 'abc'}, {'estado': 'Otra'},
            {'desdee': self.fecha.isoformat()}, {'hora_apertura': '08:00+03:00'},
            {'hora_apertura': '20:00', 'hora_cierre': '08:00'},
        ]:
            with self.subTest(cambio=cambio):
                self.assertEqual(self.client.get(self.urls[0], {**self.filtros, **cambio}).status_code, 400)

    def test_resumen_no_multiplica_totales_por_relaciones(self):
        reserva = self.reserva(aulas=[self.aula, self.otra])
        self.solicitar(reserva)
        extra = Equipamiento.objects.create(nombre='Proyector', categoria=self.equipo.categoria, trasladable=True)
        self.solicitar(reserva, cantidad=1, reservada=1, equipo=extra)
        persona = Participante.objects.create(
            nombres='Ana', apellidos='Prueba', tipo_documento='DNI', numero_documento='9999',
            fecha_nacimiento='2000-01-01', nacionalidad='Argentina', lugar_residencia='CABA',
            mail='ana@example.com', celular='1100000000',
        )
        ReservaParticipante.objects.create(reserva=reserva, participante=persona, presente=True)
        self.reserva(estado='Cancelada')
        resumen = self.consultar(self.urls[0])
        self.assertEqual(resumen['reservas_total'], 2)
        self.assertEqual(resumen['minutos_reservados'], 120)
        self.assertEqual(resumen['asistencia']['presentes'], 1)
        self.assertEqual(resumen['asistencia']['inscriptos'], 1)
        self.assertEqual(resumen['actividades_con_reserva'], 1)

    def test_ocupacion_une_superposiciones_y_conserva_espacios_sin_uso(self):
        self.reserva()
        self.reserva(inicio=time(11), fin=time(13))
        self.reserva(estado='Pendiente', inicio=time(15), fin=time(17))
        filas = self.consultar(self.urls[1])['results']
        self.assertEqual(filas[0]['minutos_ocupados'], 180)
        self.assertEqual(filas[0]['ocupacion_porcentaje'], 25)
        self.assertEqual(filas[1]['minutos_ocupados'], 0)
        recortado = self.consultar(self.urls[1], hora_apertura='11:00', hora_cierre='12:00')['results'][0]
        self.assertEqual(recortado['minutos_ocupados'], 60)
        self.assertEqual(recortado['ocupacion_porcentaje'], 100)

    def test_equipamiento_distingue_demanda_de_cantidad_asignada(self):
        self.solicitar(self.reserva(), cantidad=5, reservada=3)
        self.solicitar(self.reserva(estado='Pendiente'), cantidad=4, reservada=None)
        self.solicitar(self.reserva(estado='Cancelada'), cantidad=8, reservada=8)
        fila = self.consultar(self.urls[2])['results'][0]
        self.assertEqual(fila['reservas'], 2)
        self.assertEqual(fila['unidades_solicitadas'], 9)
        self.assertEqual(fila['unidades_minuto'], 360)

    def test_filtros_combinados_y_resultado_vacio(self):
        reserva = self.reserva()
        self.solicitar(reserva)
        resumen = self.consultar(self.urls[0], aula=self.aula.pk, equipamiento=self.equipo.pk,
                                 tipo_actividad='PRACTICA', estado='Confirmada')
        self.assertEqual(resumen['reservas_total'], 1)
        self.assertEqual(self.consultar(self.urls[0], aula=self.otra.pk)['reservas_total'], 0)

    def test_sweep_de_stock_no_suma_reservas_consecutivas(self):
        self.solicitar(self.reserva(fin=time(11)), cantidad=6, reservada=6)
        self.solicitar(self.reserva(inicio=time(11)), cantidad=6, reservada=6)
        puente = self.solicitar(self.reserva(), cantidad=4, reservada=4)
        self.assertNotIn('STOCK_SUPERADO', {a['tipo'] for a in self.alertas()})
        puente.cantidad_solicitada = puente.cantidad_reservada = 5
        puente.save()
        excesos = [a for a in self.alertas() if a['tipo'] == 'STOCK_SUPERADO']
        self.assertEqual(len(excesos), 2)
        self.assertTrue(all(a['detalles']['comprometido'] == 11 for a in excesos))

    def test_superposiciones_excluyen_canceladas_y_detectan_competidor_fuera_del_filtro(self):
        primera = self.reserva(fin=time(11))
        self.reserva(inicio=time(11))
        self.reserva(estado='Cancelada')
        self.assertNotIn('AULA_SUPERPUESTA', {a['tipo'] for a in self.alertas()})
        otra = Actividad.objects.create(
            nombre='Curso', tipo='CURSO', responsable=self.usuario, fecha_estimada=self.fecha,
            horario_inicio_estimado=time(10), horario_fin_estimado=time(12), participantes_estimados=1,
        )
        competidora = self.reserva(inicio=time(10, 30), fin=time(11), actividad=otra)
        alertas = self.alertas(reserva=primera.pk, tipo_actividad='PRACTICA')
        conflicto = next(a for a in alertas if a['tipo'] == 'AULA_SUPERPUESTA')
        self.assertCountEqual(conflicto['reserva_ids'], [primera.pk, competidora.pk])

    def test_alertas_se_resuelven_al_corregir_asignaciones_y_recursos(self):
        reserva = self.reserva(aulas=[])
        self.assertIn('RESERVA_SIN_AULA', {a['tipo'] for a in self.alertas()})
        asignar_aulas_reserva(reserva.pk, [self.aula.pk])
        self.assertNotIn('RESERVA_SIN_AULA', {a['tipo'] for a in self.alertas()})
        solicitud = self.solicitar(reserva, cantidad=4, reservada=1, critica=2)
        self.equipo.estado = 'MANTENIMIENTO'
        self.equipo.save()
        tipos = {a['tipo'] for a in self.alertas(nivel='CRITICA')}
        self.assertIn('EQUIPAMIENTO_PENDIENTE', tipos)
        self.assertIn('EQUIPO_ASIGNADO_NO_DISPONIBLE', tipos)
        solicitud.cantidad_reservada = 4
        solicitud.save()
        self.equipo.estado = 'DISPONIBLE'
        self.equipo.save()
        self.assertNotIn('EQUIPAMIENTO_PENDIENTE', {a['tipo'] for a in self.alertas()})
        self.assertNotIn('EQUIPO_ASIGNADO_NO_DISPONIBLE', {a['tipo'] for a in self.alertas()})

    def test_alertas_capacidad_fijos_mantenimiento_y_actividad_sin_reserva(self):
        self.assertIn('ACTIVIDAD_SIN_RESERVA', {a['tipo'] for a in self.alertas()})
        reserva = self.reserva()
        self.actividad.participantes_estimados = 50
        self.actividad.save()
        self.aula.estado = 'MANTENIMIENTO'
        self.aula.save()
        fijo = Equipamiento.objects.create(nombre='Fijo', categoria=self.equipo.categoria, aula=self.otra)
        self.solicitar(reserva, cantidad=1, reservada=1, equipo=fijo)
        tipos = {a['tipo'] for a in self.alertas()}
        self.assertTrue({'CAPACIDAD_INSUFICIENTE', 'AULA_NO_DISPONIBLE', 'AULA_ASIGNADA_NO_DISPONIBLE',
                         'EQUIPO_FIJO_FUERA_DE_AULA'}.issubset(tipos))
        self.assertNotIn('ACTIVIDAD_SIN_RESERVA', tipos)

    def test_consultar_alertas_no_modifica_estados_ni_historial(self):
        reserva = self.reserva(estado='Pendiente')
        # Simula una reserva antigua importada; el endpoint debe informar, no mutar.
        Reserva.objects.filter(pk=reserva.pk).update(fecha_reserva=timezone.localdate() - timedelta(days=1))
        cantidad = HistorialReserva.objects.count()
        datos = self.alertas(desde=(timezone.localdate() - timedelta(days=1)).isoformat(),
                             hasta=timezone.localdate().isoformat())
        self.assertIn('RESERVA_VENCIDA', {a['tipo'] for a in datos})
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva.estado, 'Pendiente')
        self.assertEqual(HistorialReserva.objects.count(), cantidad)

    def test_requerimiento_textual_sin_solicitud_se_informa_sin_inventar_cantidades(self):
        self.actividad.equipamiento_necesario = 'Notebooks para el taller'
        self.actividad.save()
        reserva = self.reserva()
        self.assertIn('REQUERIMIENTO_SIN_SOLICITUD', {a['tipo'] for a in self.alertas()})
        self.solicitar(reserva)
        self.assertNotIn('REQUERIMIENTO_SIN_SOLICITUD', {a['tipo'] for a in self.alertas()})

    def test_historial_captura_cambios_m2m_y_serie_de_asistencia(self):
        reserva = self.reserva(estado='Finalizada', aulas=[])
        reserva.aulas.add(self.aula)
        ultimo = HistorialReserva.objects.filter(reserva_original_id=reserva.pk).first()
        self.assertEqual(ultimo.datos['aulas'][0]['pk'], self.aula.pk)
        persona = Participante.objects.create(
            nombres='Ana', apellidos='Prueba', tipo_documento='DNI', numero_documento='9999',
            fecha_nacimiento='2000-01-01', nacionalidad='Argentina', lugar_residencia='CABA',
            mail='ana@example.com', celular='1100000000',
        )
        reserva.participantes.add(persona, through_defaults={'presente': True})
        self.assertEqual(self.consultar(self.urls[5])['serie_diaria'][0]['presentes'], 1)
        persona.reservas.clear()
        self.assertEqual(self.consultar(self.urls[5])['serie_diaria'][0]['presentes'], 0)

    def test_historial_no_duplica_snapshots_iguales_y_captura_bulk_del_servicio(self):
        reserva = self.reserva(aulas=[])
        self.assertFalse(registrar_reserva(reserva.pk))
        asignar_aulas_reserva(reserva.pk, [self.otra.pk])
        ultimo = HistorialReserva.objects.filter(reserva_original_id=reserva.pk).first()
        self.assertEqual([a['pk'] for a in ultimo.datos['aulas']], [self.otra.pk])
        self.assertFalse(registrar_reserva(reserva.pk))

    def test_historial_y_consolidado_sobreviven_borrado_sin_contar_cada_version(self):
        reserva = self.reserva(estado='Finalizada', aulas=[self.aula, self.otra])
        self.solicitar(reserva)
        pk = reserva.pk
        versiones = HistorialReserva.objects.filter(reserva_original_id=pk).count()
        self.assertGreaterEqual(versiones, 4)
        resumen = self.consultar(self.urls[5])['serie_diaria'][0]
        self.assertEqual(resumen['reservas'], 1)
        self.assertEqual(resumen['minutos_aula_finalizados'], 240)
        self.assertEqual(resumen['unidades_minuto_equipo_finalizados'], 360)
        reserva.delete()
        historial = self.consultar(self.urls[4], reserva=pk)['results']
        self.assertEqual(historial[0]['evento'], 'ELIMINADA')
        self.assertEqual(len(historial[0]['datos']['aulas']), 2)
        resumen = self.consultar(self.urls[5])['serie_diaria'][0]
        self.assertEqual(resumen['reservas'], 1)
        self.assertEqual(resumen['eliminadas'], 1)
        self.assertEqual(resumen['minutos_aula_finalizados'], 240)

    def test_snapshots_no_cambian_al_renombrar_recurso_y_no_incluyen_personas(self):
        reserva = self.reserva()
        anterior = HistorialReserva.objects.filter(reserva_original_id=reserva.pk).first()
        self.aula.nombre = 'Nombre nuevo'
        self.aula.save()
        anterior.refresh_from_db()
        self.assertEqual(anterior.datos['aulas'][0]['nombre'], 'Laboratorio')
        self.assertNotIn('numero_documento', str(anterior.datos))
        self.assertNotIn(self.usuario.username, str(anterior.datos))

    def test_snapshot_se_revierte_si_falla_la_transaccion(self):
        cantidad = HistorialReserva.objects.count()
        with self.assertRaisesMessage(RuntimeError, 'deshacer'):
            with transaction.atomic():
                self.reserva()
                raise RuntimeError('deshacer')
        self.assertEqual(HistorialReserva.objects.count(), cantidad)
        self.assertFalse(Reserva.objects.exists())

    def test_consolidacion_inicial_es_idempotente_y_reconcilia_updates(self):
        reserva = self.reserva()
        HistorialReserva.objects.all().delete()
        salida = StringIO()
        call_command('consolidar_historial', stdout=salida)
        self.assertEqual(HistorialReserva.objects.count(), 1)
        call_command('consolidar_historial', stdout=StringIO())
        self.assertEqual(HistorialReserva.objects.count(), 1)
        Reserva.objects.filter(pk=reserva.pk).update(estado_reserva=self.estados['Finalizada'])
        call_command('consolidar_historial', stdout=StringIO())
        self.assertEqual(HistorialReserva.objects.count(), 2)
        self.assertEqual(self.consultar(self.urls[5])['serie_diaria'][0]['estados'], {'Finalizada': 1})

    def test_historial_paginado_filtra_con_datos_del_snapshot(self):
        reserva = self.reserva()
        self.solicitar(reserva)
        self.reserva(aulas=[self.otra])
        data = self.consultar(self.urls[4], aula=self.aula.pk, equipamiento=self.equipo.pk)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['reserva_original_id'], reserva.pk)
        self.assertEqual(self.consultar(self.urls[4], estado='SIN_ESTADO')['count'], 0)

    def test_consultas_de_indicadores_no_crecen_por_cada_reserva(self):
        for _ in range(12):
            self.solicitar(self.reserva())
        with CaptureQueriesContext(connection) as consultas:
            data = self.consultar(self.urls[2])
        self.assertEqual(data['results'][0]['reservas'], 12)
        self.assertLessEqual(len(consultas), 8)
