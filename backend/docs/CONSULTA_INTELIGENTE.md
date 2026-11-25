# Consulta inteligente local

Se agregó una consulta sencilla de preguntas en español sobre datos reales del
centro. Es una primera versión local de reglas: no usa un modelo de lenguaje,
claves de IA, servicios externos ni datos simulados. No requiere dependencias
nuevas ni migraciones.

## Alcance y ubicación

El código está en `reportes/consulta_inteligente/` y se expone desde el archivo de
rutas de `reportes`, ya incluido en el proyecto. Reutiliza las consultas existentes
de disponibilidad, indicadores y alertas. No modifica los modelos, servicios,
endpoints de reservas, configuración general ni archivos de integración del
frontend que está preparando Abel.

La consulta solo lee información. No crea ni cambia reservas, no asigna recursos,
no registra historial de conversaciones y no muestra datos personales de usuarios
o participantes. Las respuestas de alertas pueden identificar actividades por
nombre e ID. Las consultas usan la fecha y zona horaria configuradas en Django.

## API

`GET /api/consulta-inteligente/` muestra ayuda y ejemplos.

`POST /api/consulta-inteligente/` recibe JSON:

```json
{
  "pregunta": "¿Cuántas reservas hubo este mes?",
  "limite": 5
}
```

Se autentica con `Authorization: Token <token>`. Solo permite Administración,
Coordinación y superusuarios activos. Esta ruta declara su permiso de forma
explícita y no depende del permiso global. Sin token responde 401; un usuario
sin permiso recibe 403.

`pregunta` es obligatoria, no puede quedar vacía y admite hasta 500 caracteres.
`limite` es opcional: entre 1 y 20 resultados, con valor inicial 5. `total` informa
la cantidad completa encontrada aunque se recorte la lista. El límite no cambia
los totales del resumen. No se aceptan otros campos.

La respuesta exitosa incluye:

```json
{
  "motor": "local_reglas",
  "pregunta": "¿Cuántas reservas hubo este mes?",
  "interpretacion": {
    "intencion": "resumen_reservas",
    "parametros": {"desde": "2026-11-01", "hasta": "2026-11-16"}
  },
  "respuesta": "No hay reservas registradas que coincidan con la consulta del 2026-11-01 al 2026-11-16.",
  "datos": {
    "periodo": {"desde": "2026-11-01", "hasta": "2026-11-16"},
    "reservas_total": 0,
    "reservas_por_estado": {},
    "reservas_activas": 0,
    "actividades_con_reserva": 0,
    "minutos_reservados": 0,
    "asistencia": {"inscriptos": 0, "presentes": 0, "ausentes": 0, "sin_registrar": 0},
    "serie_diaria": []
  },
  "fuentes": ["reservas", "/api/indicadores/resumen/"]
}
```

Es un ejemplo de una base sin reservas, no un resultado precargado. Las fechas,
cantidades y respuestas se calculan en cada solicitud con la información disponible.

## Preguntas admitidas

| Consulta | Ejemplo | Resultado |
| --- | --- | --- |
| Disponibilidad de espacios | ¿Qué laboratorios están disponibles mañana de 14 a 16 para 20 personas? | Espacios operativos sin superposiciones, con tipo/capacidad solicitados. |
| Resumen de reservas | ¿Cuántas reservas hubo este mes? | Totales, estados, actividades, duración y asistencia agregada. |
| Resumen por estado | ¿Cuántas reservas confirmadas hay hoy? | Resumen restringido a ese estado. |
| Ocupación de espacios | ¿Qué espacios tuvieron menor ocupación este mes? | Ranking con ocupación de referencia. También admite «mayor». |
| Uso de equipos | ¿Qué equipos tuvieron mayor utilización el mes pasado? | Ranking por unidades-minuto asignadas. |
| Demanda de equipos | ¿Qué equipos tuvieron mayor demanda este mes? | Ranking por unidades solicitadas. |
| Alertas | ¿Qué actividades tienen equipamiento pendiente mañana? | Alertas relacionadas con equipos y actividades afectadas. También admite alertas de espacios o generales. |

En disponibilidad, «espacios» incluye todos los tipos; «aulas», «laboratorios» y
«talleres» seleccionan su tipo correspondiente. El horario es obligatorio: por
ejemplo, `de 10 a 12` o `entre 10:30 y 12:00`. No se interpreta «por la tarde» sin
horas concretas. Se consulta hoy si se omite la fecha; no se ofrece disponibilidad
pasada. Los fines de semana no se ofrecen como días programables según las reglas
actuales del backend. Consultar disponibilidad no realiza ni garantiza una reserva.

## Fechas y métricas

Se reconocen `hoy`, `mañana`, `pasado mañana`, `ayer`, una fecha `YYYY-MM-DD`,
`este mes`, `mes pasado`, `esta semana`, `últimos N días` y el rango
`desde YYYY-MM-DD hasta YYYY-MM-DD`. El máximo es de 366 días inclusivos.

- `este mes`: primer día del mes hasta hoy.
- `mes pasado`: mes calendario anterior completo.
- `esta semana`: lunes de la semana hasta hoy.
- Resúmenes/rankings sin período: últimos 30 días, incluido hoy.
- Alertas sin período: hoy y los siguientes 29 días. Los avisos de estado del
  inventario describen su estado actual, aunque se consulte otro período.

La ocupación conserva la ventana de referencia de los reportes, 08:00 a 20:00.
No es una medición de presencia real. Las unidades-minuto multiplican la cantidad
reservada por la duración de reservas confirmadas/finalizadas; la demanda cuenta
las cantidades solicitadas de pendientes, confirmadas y finalizadas. No se
presentan estas métricas como predicciones.

## Cuando la pregunta no se entiende

Si la pregunta es ambigua o no está prevista, responde 400 con:

```json
{
  "codigo": "consulta_no_reconocida",
  "necesita_aclaracion": true,
  "respuesta": "Indicá el horario: por ejemplo mañana de 10 a 12.",
  "ejemplos": ["¿Cuántas reservas hubo este mes?"]
}
```

La lista real incluye varios ejemplos. Las entradas inválidas del JSON también
responden 400, con los errores por campo habituales de DRF.

Esta versión no mantiene conversaciones, no entiende cualquier pregunta y no
filtra por nombres de personas, aulas o equipos concretos. Tampoco implementa
disponibilidad de equipos, escritura de datos, predicciones o generación/ejecución
de SQL. Una pregunta fuera del alcance se rechaza en vez de responder con totales
globales que no le correspondan.

Los rankings son generales de espacios o equipos: los filtros por tipo se
admiten solo para disponibilidad. Las negaciones o exclusiones (por ejemplo,
«reservas no confirmadas») piden reformular con un estado concreto. Se responde
una sola consulta y un solo estado por pregunta.

## Cómo verificarla

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe manage.py test reportes.consulta_inteligente reportes.test_consulta_inteligente_api --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test reportes.consulta_inteligente reportes.test_consulta_inteligente_api --noinput
```

La primera orden usa una base SQLite aislada. La segunda necesita PostgreSQL
configurado y un usuario que pueda crear bases de pruebas. Las pruebas verifican
interpretación, fechas, autenticación por token, permisos, datos reales, límites,
aclaraciones y que las consultas no escriban reservas ni historial.

Resultado de verificación de esta funcionalidad: **34 pruebas nuevas aprobadas
con PostgreSQL y con SQLite**, controles de Django correctos y sin nuevas
migraciones. Son las pruebas de este módulo, no una declaración sobre el resto
del trabajo que se desarrolla en paralelo.

Para probar desde PowerShell con un token propio:

```powershell
$cabecerasConsulta = @{ Authorization = 'Token <token>' }
$preguntaConsulta = @{ pregunta = '¿Cuántas reservas hubo este mes?'; limite = 5 } | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:8000/api/consulta-inteligente/' -Method Post -Headers $cabecerasConsulta -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($preguntaConsulta))
```

Si Django estaba iniciado sin recarga automática, debe reiniciarse para cargar la
ruta nueva. No es necesario cambiar la configuración del frontend ni instalar un
proveedor de IA para usar esta primera versión.
