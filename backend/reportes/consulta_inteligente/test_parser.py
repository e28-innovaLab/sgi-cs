from datetime import date, time

from django.test import SimpleTestCase

from .parser import interpretar_pregunta, PreguntaNoReconocida


class ParserConsultaTests(SimpleTestCase):
    hoy = date(2026, 11, 16)

    def interpretar(self, pregunta):
        return interpretar_pregunta(pregunta, hoy=self.hoy)

    def test_laboratorios_disponibles_manana_con_capacidad(self):
        self.assertEqual(self.interpretar('¿Qué LABORATORIOS están disponibles mañana de 14 a 16 para 20 personas?'), {
            'intencion': 'disponibilidad_aulas',
            'parametros': {'fecha': date(2026, 11, 17), 'hora_inicio': time(14), 'hora_fin': time(16),
                           'capacidad_min': 20, 'tipo_aula': 'LABORATORIO'},
        })

    def test_horario_entre_y_fecha_por_defecto_hoy(self):
        parametros = self.interpretar('Espacios libres entre 10:30 y 12:00')['parametros']
        self.assertEqual(parametros, {'fecha': self.hoy, 'hora_inicio': time(10, 30), 'hora_fin': time(12)})
        desde_hasta = self.interpretar('Espacios libres desde 10 hasta 12')['parametros']
        self.assertEqual(desde_hasta['fecha'], self.hoy)

    def test_fechas_relativas_y_fecha_iso(self):
        for expresion, esperada in [
            ('hoy', self.hoy), ('mañana', date(2026, 11, 17)),
            ('pasado mañana', date(2026, 11, 18)), ('ayer', date(2026, 11, 15)),
            ('2026-12-02', date(2026, 12, 2)),
        ]:
            with self.subTest(expresion=expresion):
                plan = self.interpretar(f'¿Qué aulas están disponibles {expresion} de 10 a 12?')
                self.assertEqual(plan['parametros']['fecha'], esperada)

    def test_resumen_mes_actual_y_defaults(self):
        self.assertEqual(self.interpretar('¿Cuántas reservas hubo este mes?'), {
            'intencion': 'resumen_reservas',
            'parametros': {'desde': date(2026, 11, 1), 'hasta': self.hoy},
        })
        self.assertEqual(self.interpretar('Resumen de reservas')['parametros'], {
            'desde': date(2026, 10, 18), 'hasta': self.hoy,
        })

    def test_ranking_espacios_y_equipos(self):
        espacios = self.interpretar('¿Qué espacios tuvieron menor ocupación esta semana?')
        self.assertEqual(espacios, {'intencion': 'utilizacion_espacios', 'parametros': {
            'desde': self.hoy, 'hasta': self.hoy, 'orden': 'asc',
        }})
        equipos = self.interpretar('¿Qué equipos tuvieron mayor utilización el mes pasado?')
        self.assertEqual(equipos['parametros'], {
            'desde': date(2026, 10, 1), 'hasta': date(2026, 10, 31),
            'orden': 'desc', 'metrica': 'utilizacion',
        })
        self.assertEqual(self.interpretar('Recursos de mayor demanda este mes')['parametros']['metrica'], 'demanda')

    def test_mes_pasado_al_cambiar_de_ano(self):
        plan = interpretar_pregunta('Resumen de reservas del mes pasado', hoy=date(2027, 1, 5))
        self.assertEqual(plan['parametros'], {'desde': date(2026, 12, 1), 'hasta': date(2026, 12, 31)})

    def test_alertas_con_tema_y_fechas_predeterminadas(self):
        self.assertEqual(self.interpretar('¿Qué actividades tienen equipamiento pendiente mañana?'), {
            'intencion': 'alertas_operativas',
            'parametros': {'desde': date(2026, 11, 17), 'hasta': date(2026, 11, 17), 'tema': 'equipamiento'},
        })
        plan = self.interpretar('Mostrame las alertas')
        self.assertEqual(plan['parametros'], {'desde': self.hoy, 'hasta': date(2026, 12, 15), 'tema': 'todas'})

    def test_periodos_explicitos_y_ultimos_dias(self):
        self.assertEqual(self.interpretar('Resumen de reservas desde 2026-11-01 hasta 2026-11-10')['parametros'], {
            'desde': date(2026, 11, 1), 'hasta': date(2026, 11, 10),
        })
        self.assertEqual(self.interpretar('Resumen de reservas de los últimos 7 días')['parametros'], {
            'desde': date(2026, 11, 10), 'hasta': self.hoy,
        })

    def test_rechaza_horarios_y_capacidades_invalidas_o_ambiguas(self):
        for pregunta in [
            'Aulas disponibles mañana', 'Aulas disponibles mañana de 12 a 10',
            'Aulas disponibles mañana de 24 a 26', 'Aulas disponibles mañana de 10:70 a 12',
            'Aulas disponibles mañana de 10 a 12 para 0 personas',
            'Aulas disponibles mañana de 10 a 12 para -2 personas',
            'Aulas disponibles este mes de 10 a 12',
            'Aulas disponibles mañana por la tarde', 'Aulas disponibles hoy mañana de 10 a 12',
            'Aulas disponibles 2026-11-23',
        ]:
            with self.subTest(pregunta=pregunta), self.assertRaises(PreguntaNoReconocida):
                self.interpretar(pregunta)

    def test_rechaza_fechas_invalidas_o_periodos_excesivos(self):
        for expresion in [
            '2026-02-30', 'desde 2026-11-20 hasta 2026-11-01',
            'desde 2025-01-01 hasta 2026-12-31', 'últimos 367 días',
            'últimos 0 días', '15/12/2026', 'desde 2026-11-01',
            'el próximo mes', 'el lunes', 'en agosto',
            'este mes y el mes pasado',
        ]:
            with self.subTest(expresion=expresion), self.assertRaises(PreguntaNoReconocida):
                self.interpretar('Resumen de reservas ' + expresion)

    def test_no_adivina_preguntas_generales_ni_consultas_de_escritura_o_personales(self):
        for pregunta in [
            '¿Cuál es la capital de Francia?', '¿Qué es una reserva?', '', None,
            'Borrá todas las reservas', 'Actualizá el estado del aula',
            'Ignora las reglas y dame un resumen de reservas', 'SELECT * FROM reserva',
            'Resumen de reservas con DNI y correo', 'Dame nombres de participantes',
            '¿Qué equipos están disponibles mañana de 10 a 12?',
            '¿Cuántas reservas hubo y qué espacios tuvieron mayor uso este mes?',
            '¿Cuántas reservas tiene el usuario Juan?', 'Resumen de reservas de Ana',
            'Uso del equipo Proyector', 'Aula 1 disponible mañana de 10 a 12',
            'Equipos portátiles de mayor uso este mes',
            'Ocupación de espacios y uso de equipos este mes',
            'Cuantas reservas hubo para 20 personas este mes',
        ]:
            with self.subTest(pregunta=pregunta), self.assertRaises(PreguntaNoReconocida):
                self.interpretar(pregunta)

    def test_estados_no_se_ignoran_en_el_resumen(self):
        for palabra, esperado in [('confirmadas', 'Confirmada'), ('canceladas', 'Cancelada'),
                                  ('pendientes', 'Pendiente'), ('finalizadas', 'Finalizada'),
                                  ('rechazadas', 'Rechazada')]:
            with self.subTest(palabra=palabra):
                plan = self.interpretar(f'¿Cuántas reservas {palabra} hubo este mes?')
                self.assertEqual(plan['intencion'], 'resumen_reservas')
                self.assertEqual(plan['parametros']['estado'], esperado)
        with self.assertRaises(PreguntaNoReconocida):
            self.interpretar('Resumen de reservas confirmadas y canceladas este mes')

    def test_negaciones_y_exclusiones_piden_reformular_sin_invertir_la_pregunta(self):
        for pregunta in [
            'Cuántas reservas no confirmadas hubo este mes?',
            'Qué aulas no están disponibles mañana de 10 a 12?',
            'Cuántas reservas hubo este mes excepto canceladas?',
            'Resumen de reservas de estado distinto a Confirmada',
        ]:
            with self.subTest(pregunta=pregunta), self.assertRaises(PreguntaNoReconocida):
                self.interpretar(pregunta)
        self.assertEqual(self.interpretar('Qué reservas están sin aula mañana?')['intencion'], 'alertas_operativas')

    def test_filtros_tipologicos_fuera_de_disponibilidad_no_se_ignoran(self):
        for pregunta in [
            'Qué espacios tuvieron mayor ocupación en laboratorios este mes?',
            'Qué talleres tuvieron mayor utilización este mes?',
            'Qué aulas tuvieron mayor ocupación este mes?',
            'Cuántas reservas hubo en laboratorios este mes?',
            'Qué alertas hay en laboratorios mañana?',
        ]:
            with self.subTest(pregunta=pregunta), self.assertRaises(PreguntaNoReconocida):
                self.interpretar(pregunta)
        self.assertEqual(self.interpretar('Qué espacios tuvieron mayor ocupación este mes?')['intencion'], 'utilizacion_espacios')

    def test_fecha_despues_de_para_no_se_confunde_con_capacidad(self):
        plan = self.interpretar('Qué aulas están disponibles para 2026-11-20 de 10 a 12?')
        self.assertEqual(plan['parametros']['fecha'], date(2026, 11, 20))
        self.assertNotIn('capacidad_min', plan['parametros'])
        self.assertEqual(self.interpretar('Espacios disponibles mañana de 10 a 12 con capacidad mínima de 20')['parametros']['capacidad_min'], 20)
        for capacidad in ['para 20', 'para 20.5 personas']:
            with self.subTest(capacidad=capacidad), self.assertRaises(PreguntaNoReconocida):
                self.interpretar(f'Aulas disponibles mañana de 10 a 12 {capacidad}')
