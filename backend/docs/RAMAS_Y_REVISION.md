# Ramas y revisión del backend

## Trabajo identificado

- `679cf4e` (22/10/2026): entrega de etapa 2 de Leonel, usuario `Leonidas88lma`.
  El commit original conserva el correo `leogonzalez1047@gmail.com` con el que se creó.
- `dad7dac`, `9ca6709` y `f434022` (23, 26 y 27/10/2026): cambios de Abel sobre
  usuarios, actividades y participantes.
- `feature/leonel` parte de `f434022`: incluye la etapa 2 y el trabajo posterior de
  Abel. Las correcciones de esta revisión se agregan en commits nuevos de Leonel.

Se conserva `feature/abel` sin revertir ni reescribir commits. La migración
`reservas/0005_crear_actividad.py` depende de `0004_alter_estadoreserva_options.py`
de la etapa 2; además, Abel adaptó las pruebas de disponibilidad de esa entrega.
Revertir `679cf4e` completo dejaría dependencias rotas y retiraría la API sobre la
que continuó el desarrollo. Crear otra rama no elimina ni cambia la autoría de
los commits que ambas ramas comparten.

Para continuar el desarrollo de Leonel, usar `feature/leonel`. Los commits nuevos
de este repositorio usan `Leonidas88lma <leogonzalez1057@gmail.com>`.

## Correcciones de la revisión

- **Usuarios:** omitir `is_active` en una actualización completa (`PUT`) conserva
  el estado existente. Antes, el valor predeterminado del serializer reactivaba
  usuarios inactivos. Las altas siguen activas por defecto y admiten crear un
  usuario inactivo explícitamente.
- **Migración de participantes:** `0006` crea y copia las relaciones con sus
  valores de asistencia antes de quitar los campos antiguos. El rol migrado es
  `OTRO`, porque el modelo anterior no almacenaba un rol por reserva. La reversión
  restaura los datos cuando cada persona tiene una sola reserva y se rechaza si
  el modelo anterior no puede representar sus relaciones sin perderlas.

El estado final del esquema de `0006` no cambia. La corrección protege bases que
todavía no aplicaron esa migración. **Si ya se aplicó la versión anterior, Django
no la vuelve a ejecutar y los vínculos/asistencias eliminados solo pueden
recuperarse de una copia de seguridad u otra fuente fiable.** No se debe fingir
su aplicación ni revertir migraciones de una base real para intentar recuperarlos.

## Validación y límites

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Se comprueban los flujos de etapa 2 y su integración con actividades y
participantes: autenticación, permisos, catálogos, disponibilidad, validaciones de
actividad, protección del responsable, personas compartidas entre reservas,
asistencia por reserva, unicidad y conservación de datos al migrar.

Resultado de la revisión del 27/10/2026: **47 pruebas aprobadas**, comprobación de
Django sin incidencias y sin diferencias pendientes entre modelos y migraciones.

Las pruebas usan SQLite aislado, sin modificar una base de desarrollo. No
certifican PostgreSQL ni concurrencia. Las operaciones de reservas por API y sus
validaciones transaccionales siguen pendientes de la etapa 3.

Antes de migrar datos reales, revisar también estas decisiones de las migraciones
de Abel:

- `0005` asigna las actividades históricas al usuario activo `abel` o al primer
  usuario activo, usa tipo `OTRA` y estima un participante. No conserva el tipo
  libre anterior ni deduce el responsable de los usuarios asociados a la reserva.
  Requiere un usuario activo si ya existen reservas.
- `0007` agrega opciones y reduce la longitud de género y residencia. Los datos
  anteriores deben ser compatibles con esos tamaños y revisarse contra las
  opciones nuevas antes de ejecutar la migración en PostgreSQL.

Estas decisiones de conversión no se cambian sin acordar cómo representar los
datos históricos. Tener pruebas correctas no sustituye esa revisión de datos.
