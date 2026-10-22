# Etapa 2: acceso y gestión por API

## Por qué este es el siguiente paso

La etapa 1 existente contiene los modelos `Usuario`, `Rol`, `Aula`, `Categoria`, `Equipamiento`, `Reserva` y sus relaciones; migraciones; panel de administración; y `GET /api/aulas-disponibles/` con una primera regla de superposición.

Tener modelos permite guardar información, pero el frontend necesita operaciones HTTP para usarla. Además, antes de habilitar modificaciones hay que resolver quién puede realizarlas. Por eso esta etapa completa el acceso y los catálogos que luego utilizará el motor de reservas.

El alcance se basa en los requisitos de usuarios, roles, espacios y recursos del PDF del proyecto. La división en cuatro etapas es una propuesta para el backend: no reproduce los seis sprints del documento ni implica que el MVP completo esté terminado.

## Las cuatro etapas del backend

| Etapa | Resultado | Criterio de cierre |
| --- | --- | --- |
| 1. Base del sistema | Configuración Django/PostgreSQL, entidades y relaciones, migraciones, admin y consulta inicial de disponibilidad. | El modelo inicial persiste datos y permite explorar la disponibilidad. |
| 2. Acceso y catálogos | Login/logout, roles, gestión de usuarios y API de espacios y equipamiento. | El frontend puede autenticarse, cargar datos y consultarlos con permisos validados por el backend. |
| 3. Reservas y agenda | API de actividades/reservas, responsables, participantes estimados, asignación de espacios y recursos, disponibilidad de equipos, confirmación, modificación y cancelación. | Un flujo de reserva válido se guarda completo y uno incompatible no deja asignaciones parciales; las solicitudes simultáneas no duplican recursos. |
| 4. Integración y gestión inteligente | Importación CSV/Excel con validación, indicadores de uso y demanda, alertas y consultas de datos para BI/IA; pruebas integrales y despliegue. | Los flujos mínimos del MVP funcionan con frontend y datos reales, incluyendo consultas inteligentes basadas en la base de datos. |

## Implementación de la etapa 2

Se mantiene Django y Django REST Framework. No se necesitan dependencias adicionales: se habilita `rest_framework.authtoken`, incluido en DRF.

- `usuarios/serializers.py`: valida credenciales y datos personales; usa los validadores de contraseñas de Django y almacena su hash.
- `usuarios/permissions.py`: centraliza los permisos de administración y coordinación.
- `usuarios/views.py`: expone login, logout, perfil, roles y gestión de usuarios.
- `espacios/serializers.py`: define el contrato de aulas, categorías y equipos, y valida capacidades, cantidades y ubicación del equipo fijo.
- `espacios/views.py`: implementa altas, consultas, modificaciones, eliminación y cambios de estado; incorpora búsquedas y filtros.
- `reservas/services.py`: conserva la regla existente de superposición e incorpora el estado operativo del aula.
- `reservas/serializers.py`: valida fechas, horas y capacidad solicitada antes de consultar disponibilidad.
- Las nuevas migraciones agregan campos de aula, crean roles sin duplicarlos y sincronizan dos diferencias ya existentes entre modelos y migraciones: el manager de usuarios y el orden de estados de reserva.

Las aulas incorporan `tipo`, `ubicacion`, `caracteristicas` y `estado`. Al migrar, las aulas existentes reciben tipo `AULA`, estado `DISPONIBLE` y textos vacíos; luego Administración puede completar los datos reales. Se mantienen las tablas y relaciones existentes.

## Roles y permisos

| Operación | ADMIN | COORDINACION |
| --- | --- | --- |
| Login, logout, consultar perfil | Sí | Sí |
| Consultar roles | Sí | Sí |
| Crear, consultar y modificar usuarios | Sí | No |
| Consultar aulas, categorías y equipos | Sí | Sí |
| Crear, editar o eliminar aulas, categorías y equipos | Sí | No |
| Cambiar el estado operativo de aulas y equipos | Sí | Sí, mediante el endpoint específico de estado |
| Consultar aulas disponibles | Sí | Sí |

El superusuario Django también tiene acceso administrativo. El rol `ADMIN` de la API no concede `is_staff` ni `is_superuser`; esos privilegios no se modifican mediante esta API. Un administrador común no puede modificar un superusuario.

Los usuarios se desactivan con `PATCH {"is_active": false}`. No hay eliminación de usuarios por API para conservar referencias históricas. Tampoco se permite que un administrador se desactive a sí mismo o se quite su propio rol administrativo.

## Contrato HTTP

Todos los endpoints terminan en `/`. Se envía JSON con `Content-Type: application/json`. Excepto login, todos requieren:

```http
Authorization: Token <token_obtenido_en_login>
```

### Autenticación y usuarios

| Método | Ruta | Uso |
| --- | --- | --- |
| POST | `/api/auth/login/` | Recibe `username` y `password`; devuelve `token` y `usuario` con su rol. |
| POST | `/api/auth/logout/` | Revoca el token y responde 204. |
| GET | `/api/auth/me/` | Devuelve el perfil autenticado. |
| GET | `/api/roles/` | Lista los dos roles disponibles y sus identificadores. |
| GET, POST | `/api/usuarios/` | Lista usuarios o crea uno. Solo ADMIN. |
| GET, PUT, PATCH | `/api/usuarios/{id}/` | Consulta o modifica un usuario. Solo ADMIN. |

Datos para crear un usuario:

```json
{
  "username": "coordinacion",
  "password": "UsarUnaClavePropia!8492",
  "first_name": "Ana",
  "last_name": "Gomez",
  "email": "ana@example.com",
  "tipo_documento": "DNI",
  "numero_documento": "30111222",
  "rol": 2
}
```

El valor de `rol` se obtiene de `/api/roles/`; el `2` es ilustrativo y no debe asumirse fijo. La contraseña es obligatoria al crear y opcional al editar. Nunca se devuelve en respuestas. Cambiarla o desactivar al usuario revoca su token anterior.

Se utiliza un token opaco por usuario, reutilizado en nuevos logins y sin vencimiento automático. Logout lo invalida para todos los clientes que compartan ese token. Es una solución inicial; si luego se requieren sesiones por dispositivo o vencimiento, hay que extender esta capa. Se limita login a 10 solicitudes por minuto por IP mediante la caché de Django; el despliegue con varios procesos necesita una caché compartida y configuración del proxy. Para publicar la API, el token debe viajar por HTTPS.

### Catálogos

| Métodos | Ruta | Uso |
| --- | --- | --- |
| GET, POST | `/api/aulas/` | Consultar o crear espacios. |
| GET, PUT, PATCH, DELETE | `/api/aulas/{id}/` | Operar sobre un espacio. |
| PATCH | `/api/aulas/{id}/estado/` | Actualizar únicamente su estado. |
| GET | `/api/aulas/{id}/equipamientos/` | Consultar los equipos asociados al espacio. |
| GET, POST | `/api/categorias/` | Consultar o crear categorías. |
| GET, PUT, PATCH, DELETE | `/api/categorias/{id}/` | Operar sobre una categoría. |
| GET, POST | `/api/equipamientos/` | Consultar o crear equipos. |
| GET, PUT, PATCH, DELETE | `/api/equipamientos/{id}/` | Operar sobre un equipo. |
| PATCH | `/api/equipamientos/{id}/estado/` | Actualizar únicamente su estado. |

Ejemplo de alta de aula:

```json
{
  "nombre": "Laboratorio de simulación 1",
  "tipo": "LABORATORIO",
  "ubicacion": "Planta baja",
  "caracteristicas": "Cuenta con proyector",
  "capacidad": 20,
  "sillas": 20,
  "mesas": 5,
  "estado": "DISPONIBLE"
}
```

Tipos admitidos: `AULA`, `LABORATORIO`, `TALLER`, `OTRO`. Estados de aula y equipo: `DISPONIBLE`, `MANTENIMIENTO`, `FUERA_SERVICIO`.

Ejemplo de alta de equipamiento trasladable:

```json
{
  "nombre": "Notebook",
  "categoria": 1,
  "aula": null,
  "cantidad": 10,
  "estado": "DISPONIBLE",
  "trasladable": true
}
```

Se usan identificadores reales de categoría y aula. Un equipo fijo (`trasladable: false`) requiere un aula; uno trasladable puede tener una ubicación habitual o quedar sin aula asignada. `cantidad` y `capacidad` deben ser al menos 1. Sillas y mesas admiten 0. Las respuestas conservan los identificadores propios del modelo: `id_aula`, `id_categoria`, `id_equipo`, `id_usuario`.

El endpoint de estado requiere exactamente el campo `estado` y rechaza intentos de modificar otros campos:

```json
{"estado": "MANTENIMIENTO"}
```

La eliminación de una categoría o equipo referenciado responde 409. Eliminar un aula con reservas o equipos también responde 409; primero debe resolverse su relación con esos datos.

### Búsqueda, filtros y paginación

- Aulas: `?search=simulacion&tipo=LABORATORIO&estado=DISPONIBLE&capacidad_min=20`.
- Equipos: `?search=notebook&categoria=1&aula=1&estado=DISPONIBLE&trasladable=true`.
- Usuarios: `?search=ana` (solo ADMIN).
- Categorías: `?search=tecnologia`.

Los listados de catálogos, usuarios, roles y equipos por aula se paginan de a 50 registros:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [{"id_categoria": 1, "nombre": "Tecnología"}]
}
```

La página siguiente se solicita con `?page=2`. Un filtro tipado inválido devuelve 400.

### Disponibilidad de aulas

```http
GET /api/aulas-disponibles/?fecha=2027-01-15&hora_inicio=10:00&hora_fin=12:00&capacidad_min=20
```

`fecha`, `hora_inicio` y `hora_fin` son obligatorios. `capacidad_min` es opcional. Las horas se interpretan como horario local del centro y aceptan `HH:MM` o `HH:MM:SS`, sin offset. La hora final debe ser posterior a la inicial dentro del mismo día.

La respuesta exitosa conserva el formato de la etapa 1, una lista sin paginar:

```json
[{"id": 1, "nombre": "Aula 1", "capacidad": 20}]
```

Reglas verificadas:

- Solo se ofrecen aulas con estado `DISPONIBLE`.
- Una reserva `Pendiente` o `Confirmada` bloquea un aula si sus intervalos se superponen.
- Una reserva que termina a las 12:00 permite otra que empieza a las 12:00.
- Las canceladas, rechazadas o de otra fecha no bloquean.
- Se respeta la capacidad mínima, si se solicita.

**Cambio para cualquier consumidor existente:** esta consulta ahora requiere autenticación y los errores de validación usan el formato de DRF por campo, en lugar de `{"error": "..."}`.

### Respuestas de error

- 400: datos o filtros inválidos; normalmente un objeto con campos y listas de mensajes, como `{"capacidad": ["..."]}`. Las validaciones generales usan `non_field_errors`.
- 401: token ausente, inválido, revocado o usuario inactivo.
- 403: usuario autenticado sin permiso para la operación.
- 404: recurso inexistente.
- 405: método no habilitado, por ejemplo eliminar usuarios.
- 409: eliminación impedida por relaciones.
- 429: exceso de solicitudes de login.

Los errores de autenticación, permisos y relaciones usan `{"detail": "..."}`.

## Demostración desde PowerShell

Con las migraciones aplicadas, un superusuario creado y el servidor ejecutándose, abrí otra consola:

```powershell
$apiCentro = 'http://127.0.0.1:8000/api'
$credencialCentro = Get-Credential -Message 'Usuario creado con createsuperuser'
$loginCentro = @{
    username = $credencialCentro.UserName
    password = $credencialCentro.GetNetworkCredential().Password
} | ConvertTo-Json
$sesionCentro = Invoke-RestMethod "$apiCentro/auth/login/" -Method Post -ContentType 'application/json' -Body $loginCentro
$cabecerasCentro = @{ Authorization = "Token $($sesionCentro.token)" }

Invoke-RestMethod "$apiCentro/auth/me/" -Headers $cabecerasCentro
Invoke-RestMethod "$apiCentro/roles/" -Headers $cabecerasCentro

$aulaCentro = Invoke-RestMethod "$apiCentro/aulas/" -Method Post -Headers $cabecerasCentro -ContentType 'application/json' -Body (@{
    nombre = 'Aula de prueba etapa 2'
    capacidad = 20
    tipo = 'LABORATORIO'
} | ConvertTo-Json)

Invoke-RestMethod "$apiCentro/aulas-disponibles/?fecha=2027-01-15&hora_inicio=10:00&hora_fin=12:00" -Headers $cabecerasCentro

Invoke-RestMethod "$apiCentro/aulas/$($aulaCentro.id_aula)/estado/" -Method Patch -Headers $cabecerasCentro -ContentType 'application/json' -Body '{"estado":"MANTENIMIENTO"}'

# El aula de prueba ya no aparece entre las disponibles.
Invoke-RestMethod "$apiCentro/aulas-disponibles/?fecha=2027-01-15&hora_inicio=10:00&hora_fin=12:00" -Headers $cabecerasCentro
Invoke-RestMethod "$apiCentro/auth/logout/" -Method Post -Headers $cabecerasCentro
```

Para frontend, enviar el mismo encabezado `Authorization` en las solicitudes y tratar 401 como sesión inválida. En desarrollo con puertos distintos, configurar un proxy de `/api` hacia Django en el servidor del frontend; esta entrega no configura CORS entre orígenes.

## Verificación y límites

Las pruebas automatizadas cubren autenticación, contraseñas, revocación de tokens, permisos, CRUD, filtros, paginación, integridad de relaciones y disponibilidad con diferentes superposiciones y estados. Se ejecutan con `python manage.py test --settings=config.test_settings`, usando SQLite en memoria. No sustituyen la validación posterior contra PostgreSQL ni las pruebas de concurrencia de la etapa 3. Los settings de pruebas usan un hash rápido exclusivamente para pruebas; el entorno normal conserva los hashers de Django.

Esta etapa no expone altas o modificaciones de reservas por API. Los modelos y el admin de reservas de la etapa 1 siguen siendo la base para el próximo desarrollo. Los estados operativos nuevos no implementan todavía bloques de mantenimiento por rango de fechas ni generan alertas ante reservas previas.

Los equipos existentes con estado vacío o sin ubicación deben revisarse al completar la carga inicial. Las nuevas validaciones de equipos se aplican en la API; no se hace una normalización automática de datos anteriores ni se crean reglas nuevas de reserva.

## Cómo desarrollar la etapa 3 sobre esta base

1. Acordar el flujo de estados de reserva y normalizar datos anteriores sin estado. Completar el modelo de actividad/reserva con responsable y cantidad estimada de participantes, conservando las tablas existentes cuando sea posible.
2. Crear serializers para solicitudes con aulas y equipos; mantener la asignación y sus validaciones en servicios reutilizables, no dentro de las vistas.
3. Validar capacidad, horarios, estado operativo, equipos fijos dentro del espacio seleccionado y cantidades de recursos trasladables disponibles. Para calcular stock por intervalo, contemplar las reservas activas simultáneas y evitar sumar reservas que nunca se superponen entre sí.
4. Ejecutar la validación final y el guardado en una misma transacción PostgreSQL, bloqueando filas de aulas y equipos en un orden consistente para evitar asignaciones duplicadas y bloqueos cruzados. La consulta previa de disponibilidad es orientativa.
5. Exponer creación, modificación, confirmación y cancelación; impedir transiciones inválidas. Cancelar debe liberar espacios y cantidades reservadas de forma coherente.
6. Proveer un endpoint de agenda filtrado por rango de fechas, aula y estado para el calendario del frontend, y consultas de faltantes para las alertas posteriores.
7. Probar reservas válidas, superposición, capacidad insuficiente, falta de stock, mantenimiento, actualización sin conflicto consigo misma, cancelación y dos solicitudes simultáneas sobre PostgreSQL.
