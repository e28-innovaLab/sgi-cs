# Indicadores, alertas e información histórica

El módulo `reportes` ofrece consultas de solo lectura para Administración,
Coordinación y superusuarios activos. Usa la autenticación existente:
`Authorization: Token <token>`. Sin token responde 401; sin rol habilitado, 403;
filtros inválidos, 400. POST, PUT, PATCH y DELETE no están habilitados.

## Instalación y consolidación inicial

Desde `backend`, con PostgreSQL configurado en `.env`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py consolidar_historial
```

La migración agrega una tabla de historial; no cambia los modelos operativos de
Abel. El comando captura el estado disponible de cada reserva y es idempotente:
otra ejecución solo agrega una versión si los datos cambiaron. Se puede ejecutar
periódicamente como reconciliación de importaciones o escrituras masivas externas.
No reconstruye transiciones, recursos ni asistencias anteriores que nunca se
registraron. No hay datos de demostración ni respuestas simuladas.

Si Django ya estaba ejecutándose sin recarga automática, reiniciar ese servidor
para cargar la aplicación y las rutas nuevas después de aplicar la migración.

## Endpoints y filtros

| GET | Resultado |
| --- | --- |
| `/api/indicadores/resumen/` | Totales de reservas, estados, actividades con reserva, duración, asistencia agregada y serie diaria. |
| `/api/indicadores/espacios/` | Reservas y ocupación de referencia por aula, incluyendo aulas sin uso. Orden descendente por minutos ocupados. |
| `/api/indicadores/equipamiento/` | Demanda, cantidad de reservas y unidades-minuto asignadas por equipo, incluyendo equipos sin demanda. |
| `/api/alertas/` | Problemas actuales de reservas, capacidad, asignaciones, stock y estado de recursos. |
| `/api/historial/reservas/` | Versiones registradas de reservas, incluso eliminadas. Más recientes primero. |
| `/api/historial/utilizacion/` | Serie diaria consolidada a partir de la última versión de cada reserva; conserva las eliminadas. |

Filtros comunes:

- `desde` y `hasta`: fechas `YYYY-MM-DD`, inclusivas. Máximo 366 días.
- `aula`, `equipamiento`, `reserva`: identificadores enteros positivos.
- `tipo_actividad`: `CURSO`, `PRACTICA`, `WORKSHOP`, `CAPACITACION` u `OTRA`.
- `estado`: `Pendiente`, `Confirmada`, `Cancelada`, `Rechazada`, `Finalizada` o
  `SIN_ESTADO`.
- `hora_apertura` y `hora_cierre`: solo afectan la ocupación de referencia de
  espacios. Horario local del centro, `HH:MM` o `HH:MM:SS`, sin offset.
- `nivel`: solo afecta alertas; `ADVERTENCIA` o `CRITICA`.
- `page`: página del listado. Los filtros desconocidos devuelven 400.

Sin fechas, indicadores e historial consultan los últimos 30 días hasta hoy;
alertas consulta hoy y los siguientes 29 días. Si solo se indica `desde`, se
consulta desde esa fecha y 29 días más; si solo se indica `hasta`, se toman los
29 días anteriores. En alertas, indicar solo `hasta` conserva hoy como inicio.

Los filtros de actividad, reserva, estado y recursos seleccionan reservas. Los
catálogos de indicadores conservan los recursos sin uso con valor cero; `aula`
restringe el catálogo de espacios y `equipamiento`, el catálogo de equipos.
Al filtrar equipamiento por aula se incluyen sus equipos habituales y los móviles
solicitados por las reservas seleccionadas.

Espacios, equipamiento, alertas e historial de versiones se paginan de a 50:

```json
{"count": 0, "next": null, "previous": null, "results": []}
```

El resumen devuelve un objeto y las series diarias incluyen las fechas con datos,
ordenadas por fecha. No se crean filas artificiales para días sin registros.

Ejemplos:

```http
GET /api/indicadores/resumen/?desde=2026-11-01&hasta=2026-11-30
GET /api/indicadores/espacios/?desde=2026-11-01&hasta=2026-11-30&hora_apertura=08:00&hora_cierre=18:00
GET /api/indicadores/equipamiento/?desde=2026-11-01&hasta=2026-11-30&equipamiento=1
GET /api/alertas/?desde=2026-11-01&hasta=2026-11-30&nivel=CRITICA
GET /api/historial/reservas/?desde=2026-11-01&hasta=2026-11-30&reserva=1
GET /api/historial/utilizacion/?desde=2026-11-01&hasta=2026-11-30&aula=1
```

Los identificadores del ejemplo deben reemplazarse por los reales.

## Definiciones de los indicadores

El resumen y los rankings consultan las reservas operativas actuales. Cada reserva
se cuenta una vez, aunque tenga varias aulas, solicitudes o participantes.
`actividades_con_reserva` cuenta actividades distintas vinculadas a esas reservas;
no incluye actividades sin reserva. `reservas_activas` suma pendientes y confirmadas.

- **Minutos reservados:** suma de las duraciones de reservas confirmadas y
  finalizadas, una vez por reserva. Las pendientes, canceladas, rechazadas y sin
  estado no suman tiempo. Los minutos de reservas futuras confirmadas son
  planificación, no una medición de presencia real.
- **Asistencia:** personas inscriptas, presentes, ausentes y sin registrar en
  reservas confirmadas o finalizadas. Una misma persona cuenta por cada reserva;
  no son personas únicas del período. No se exponen documentos, correos ni nombres.
- **Ocupación por aula:** unión de los intervalos confirmados/finalizados por día,
  recortados a la ventana solicitada. No se duplica el tiempo de una superposición.
  Porcentaje = minutos de esa unión / minutos de referencia × 100.
- **Ventana de referencia:** por defecto 08:00 a 20:00, todos los días del rango.
  Es una referencia explícita para comparación, no el horario institucional real:
  el modelo no tiene calendario laboral ni historial de mantenimiento. No se
  descuentan feriados o períodos de mantenimiento. `estado_actual` describe hoy,
  no el estado histórico del aula.
- **Demanda de equipos:** suma de `cantidad_solicitada` de pendientes, confirmadas
  y finalizadas. Canceladas y rechazadas se excluyen.
- **Unidades-minuto:** suma de cantidad efectivamente reservada × duración de
  confirmadas/finalizadas. Una cantidad reservada nula aporta cero; no se inventa
  una asignación a partir de lo solicitado. El stock y estado mostrados son actuales.

## Reglas de alertas

Cada alerta contiene `id` estable mientras el problema no cambie, `tipo`, `nivel`,
`mensaje`, `reserva_ids`, `aula_id`, `equipamiento_id`, `fecha`, intervalo y
`detalles`. Los campos no aplicables son nulos. Las críticas aparecen primero.

| Tipo | Regla |
| --- | --- |
| `AULA_NO_DISPONIBLE`, `EQUIPO_NO_DISPONIBLE` | Estado actual de mantenimiento, fuera de servicio o sin estado operativo válido. Son alertas del inventario actual, independientes del rango de fechas. |
| `RESERVA_SIN_ESTADO` | Reserva sin estado definido. |
| `RESERVA_SIN_AULA` | Reserva activa sin aula asignada. |
| `CAPACIDAD_INSUFICIENTE` | Participantes estimados mayores que la suma de capacidades de las aulas asignadas. Crítica. |
| `AULA_ASIGNADA_NO_DISPONIBLE`, `EQUIPO_ASIGNADO_NO_DISPONIBLE` | Recurso de una reserva activa que dejó de estar operativo. Crítica. |
| `EQUIPO_FIJO_FUERA_DE_AULA` | Equipo fijo cuya ubicación no está entre las aulas asignadas. Crítica. |
| `EQUIPAMIENTO_PENDIENTE` | Cantidad reservada menor que la solicitada; crítica si además no alcanza la cantidad crítica. |
| `REQUERIMIENTO_SIN_SOLICITUD` | La actividad tiene un requerimiento textual de equipamiento, pero la reserva activa no tiene solicitudes. Advertencia; el texto no permite deducir cantidades ni verificar cobertura completa. |
| `AULA_SUPERPUESTA` | Más de una reserva activa en la misma aula durante un tramo. Crítica. |
| `STOCK_SUPERADO` | Suma de unidades comprometidas simultáneas mayor que el stock actual. Crítica. |
| `RESERVA_VENCIDA` | Pendiente cuyo inicio pasó, o confirmada cuyo fin pasó, sin actualizar estado. |
| `ACTIVIDAD_SIN_RESERVA` | Actividad del rango estimado sin reservas pendientes, confirmadas ni finalizadas. |

Pendiente y Confirmada son los estados activos. Los intervalos son `[inicio, fin)`:
terminar a las 11:00 permite empezar otra reserva a las 11:00. El stock se evalúa
por tramos simultáneos, no sumando indiscriminadamente todas las reservas del rango.
Como en el servicio operativo existente, cuando `cantidad_reservada` es nula se
considera la cantidad solicitada como compromiso para detectar conflictos.

Los conflictos consideran también competidores fuera de los filtros de actividad
o reserva, y se informan si afectan al menos una reserva seleccionada. Así, filtrar
una reserva no oculta su conflicto con otra. Las alertas de actividad sin reserva
no se calculan al filtrar aula, equipo, reserva o estado porque esa asignación aún
no existe.

GET no modifica reservas, no finaliza estados ni escribe historial. Las alertas se
recalculan y desaparecen al resolver su causa; no se envían emails, notificaciones
ni mensajes. El comando existente `finalizar_reservas` conserva su función.

## Historial y consolidación

Cada versión guarda fecha y horario de reserva, estado, actividad, estimación de
participantes, aulas con nombres/capacidades, equipos con cantidades y asistencia
agregada. Las versiones anteriores no se actualizan cuando cambian los catálogos.
La tabla no tiene FK a reservas: el borrado operativo conserva los registros y
agrega un evento `ELIMINADA` con las relaciones previas al borrado.

Se capturan altas/cambios de reservas, actividad, asignaciones, solicitudes y
asistencia con los eventos ORM normales. Las asignaciones masivas del servicio
`asignar_aulas_reserva` se registran explícitamente, porque `bulk_create` no emite
señales. Cambios de aulas/participantes por los managers ManyToMany también se
registran. Una transacción fallida revierte sus snapshots. No se identifica al
autor de la operación: los servicios actuales no lo reciben en todos los flujos.

Es un historial de estados observados para BI, no una auditoría forense: escrituras
SQL directas, `QuerySet.update` y operaciones masivas externas deben llamar a la
consolidación; esta recupera el estado final, no cambios intermedios omitidos. El
historial no tiene endpoints de escritura ni edición en el admin.

`/historial/utilizacion/` toma **solo la última versión conocida de cada reserva**,
filtrando por su fecha de reserva más reciente. No cuenta cada versión como una
reserva adicional. Retiene las eliminadas y devuelve:

- `reservas`, `eliminadas` y `estados`: cantidad de reservas consolidadas por fecha.
- `minutos_aula_finalizados`: duración × cantidad de aulas del snapshot, solo en
  Finalizada. Es tiempo asignado registrado; no mide presencia ni une conflictos.
- `unidades_minuto_equipo_finalizados`: duración × cantidades reservadas del snapshot.
- `presentes`: asistencia registrada en esas reservas finalizadas.

Filtrar aula/equipamiento utiliza los identificadores del snapshot, aunque el
recurso ya no exista. Esto permite analizar utilización pasada sin depender de
nombres, cantidades o capacidades actuales. Los reportes operativos excluyen
reservas borradas; esta serie histórica las conserva explícitamente.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Las pruebas cubren permisos, filtros, conteos sin multiplicación por relaciones,
ocupación, conflictos reales y consecutivos, faltantes, resolución de alertas,
captura transaccional, borrado, consolidación idempotente y consultas de indicadores
sin una consulta adicional por cada reserva.

Verificado localmente: 72 pruebas aprobadas tanto con PostgreSQL como con SQLite;
controles de Django correctos y modelos alineados con las migraciones.
