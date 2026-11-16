# Revisión del proyecto y pendientes del MVP — 16/11/2026

## Qué se descargó y dónde está

Se actualizaron las referencias de todas las ramas del remoto `origin`.

| Rama remota | Último commit observado | Estado local |
| --- | --- | --- |
| `main` | `4f0f1ca`, 04/11 | Sin cambios nuevos desde la revisión anterior. |
| `feature/abel` | `b1d1914`, 10/11 | Descargada e integrada en la rama local `feature/leonel`. |
| `feature/leonel` | `061c854`, 05/11 | Conserva los reportes, alertas e historial. La integración de esta revisión es local. |
| `feature/siges-frontend` | `b61fb31`, 05/11 | Worktree actualizado por fast-forward. Incluye la reorganización en carpetas. |

El backend de trabajo es `sgi-cs/backend`. El worktree del frontend está en
`sgi-cs/frontend` y, tras la reorganización de esa rama, la aplicación React está
en `sgi-cs/frontend/frontend`. Su carpeta `backend` contiene una copia anterior;
no es el backend integrado de Leonel. Se adaptó el iniciador local para detectar
la estructura nueva sin modificar código del frontend.

Las ramas comparten un repositorio, pero el trabajo reciente todavía no está
consolidado en `main`. Descargar todo no implica que todo esté integrado en una
misma rama. No se hizo push durante esta revisión. Tampoco se pueden revisar
cambios que otros integrantes aún no hayan publicado en GitHub.

## Cambios recientes de Abel

El commit `b1d1914` incorpora:

- Prohibición de actividades y reservas en sábados y domingos.
- Control de capacidad al asignar aulas y asociar participantes.
- Rol `SOLICITANTE` y migración `usuarios/0004_crear_rol_solicitante`.
- Cambios en permisos: confirmación/rechazo solo por Administración, modificación
  de catálogos solo por Administración y lectura de usuarios para Coordinación.
- Permiso global de API que admite cualquier usuario autenticado y activo.

La integración por Git fue limpia y conservó el módulo `reportes` y la captura
explícita de historial en las asignaciones masivas de aulas. Eso no garantiza
compatibilidad funcional: se detectaron las siguientes incidencias.

## Incidencias prioritarias comprobadas

1. **Protección de superusuarios perdida.** `UsuarioViewSet` pasó a usar
   `SoloAdministradorParaEscritura`, que no conserva el permiso por objeto de
   `SoloAdministrador`. La prueba de desactivar un superusuario con un administrador
   común devuelve 200 cuando esperaba 403. Corregir antes de publicar/desplegar.
2. **Acceso a reportes ampliado por el permiso global.** Las vistas de reportes
   heredan ahora `EsUsuarioActivo`; la prueba permite leerlos con un rol ajeno a
   ADMIN/COORDINACION. Deben declarar explícitamente su política de permisos si se
   mantiene el alcance documentado.
3. **SOLICITANTE incompleto.** La migración crea el rol, pero `LoginSerializer`
   rechaza su login y el campo `rol` de `UsuarioSerializer` todavía admite solo
   ADMIN/COORDINACION. Se comprobó login 400 con credenciales válidas y mensaje
   «El usuario no tiene un rol habilitado».
4. **Disponibilidad de equipamiento subestimada.** El servicio suma todas las
   solicitudes que intersectan el rango consultado, aunque no coincidan entre sí.
   Diagnóstico reproducido en una base de pruebas: stock 10, una reserva 10–11 de
   6 unidades y otra 11–12 de 6; al consultar 10–12 deberían quedar 4 unidades,
   pero el servicio no ofrece el equipo. Las alertas ya usan un barrido temporal;
   disponibilidad y confirmación deben alinearse con esa lógica.
5. **Inicialización de estados pendiente.** En una base vacía, aplicar todas las
   migraciones deja cero registros de `EstadoReserva`. Hace falta una carga
   idempotente de Pendiente, Confirmada, Cancelada, Rechazada y Finalizada para
   que los servicios y el admin funcionen sin preparación manual adicional.
6. **Pruebas y documentación desalineadas con las reglas nuevas.** Se sigue
   esperando que Coordinación cambie estados de catálogos y que no liste usuarios;
   Abel cambió ambas reglas. Otra prueba intenta crear una reserva en sábado.
   Acordar con el equipo/Centro la matriz de permisos y la restricción de fines
   de semana; después actualizar pruebas y documentación. No cambiar resultados
   esperados solo para ocultar las regresiones de seguridad anteriores.

No se corrigieron estas reglas de negocio durante la descarga/revisión; quedan
identificadas para la siguiente tarea. El backend resultante no debe considerarse
listo para producción por el solo hecho de que el merge no tuvo conflictos.

## Estado frente a las consignas

Referencia: PDF de consignas aportado para el trabajo, páginas 7–9 (MVP y flujos
de aprobación) y 12–13 (sectores y primeras semanas).

| Área | Existe | Falta para completar el flujo |
| --- | --- | --- |
| Usuarios y catálogos | Login/token, roles, API de usuarios, aulas, categorías y equipos. | Resolver permisos y completar SOLICITANTE; integrar autenticación con la interfaz. |
| Actividades y reservas | Modelos, admin y servicios de asignación, confirmación, cancelación, participantes y asistencia. | Endpoints de creación/edición/listado de actividades y reservas, acciones de estado, asignaciones y participantes/asistencia. Los servicios aún no forman una API operativa completa. |
| Disponibilidad | GET de aulas y servicio de equipos. | Exponer disponibilidad de equipos por intervalo y corregir el cálculo de stock simultáneo; comprobar concurrencia real. |
| Indicadores/alertas/historial | Seis endpoints, consolidación y snapshots conservados tras borrados. | Restablecer permisos, conectarlos al dashboard y acordar fórmulas/horarios con BI. La ocupación de referencia incluye todos los días aunque ahora se prohíben reservas en fin de semana; confirmar el denominador institucional. |
| Frontend | Navegación, formularios, listados y dashboard visual. | Login real, consumo de API, permisos visibles, datos persistidos en PostgreSQL y mensajes de errores del servidor. Usa `localStorage`, catálogos fijos y un gráfico de asistencia con valores escritos en el código. |
| Agenda | Listado local de reservas accesible desde el menú Calendario. | Agenda real por día/semana/mes, filtros y detalle desde API. |
| Importación | Carga manual por catálogos/API/admin. | CSV o Excel con validación y reporte de errores. Es requisito del MVP. |
| Mantenimiento | Estado operativo de espacios/equipos y alertas. | Bloqueos temporales por rango y tratamiento de reservas previamente asignadas. |
| Consulta inteligente | Datos e indicadores utilizables como base. | Consulta en lenguaje natural con información real, autorización y reglas de negocio resueltas por el backend. El PDF la exige para el MVP. |
| QA y entrega | Suite automatizada de backend y compilación frontend. | Resolver incidencias, pruebas de los flujos completos, concurrencia en PostgreSQL, datos de demostración coherentes, despliegue y configuración del entorno de entrega. |

Predicción avanzada, recomendaciones/optimización automáticas y seguimiento de
trayectorias estudiantiles aparecen como evolución futura: no deben desplazar
los requisitos mínimos de integración, importación y consulta inteligente.

## Orden sugerido de trabajo

1. Backend/equipo: acordar permisos y resolver las seis incidencias anteriores.
2. Backend: completar la API de actividades/reservas/asignaciones/participantes,
   disponibilidad de equipos y consulta de agenda, reutilizando los servicios.
3. Frontend + backend: integrar login y un flujo completo actividad → reserva →
   recursos → confirmación/cancelación → agenda; luego dashboard y alertas.
4. Backend + datos/BI: importación validada y métricas sobre datos reales.
5. IA + backend: consultas en lenguaje natural usando las consultas autorizadas.
6. QA + todo el equipo: demostrar los seis flujos del PDF y preparar la entrega.

## Verificación realizada

- Backend SQLite: **72 pruebas ejecutadas, 6 fallos y 1 error**. Los fallos son
  dos subcasos de actualización de estado por Coordinación, acceso a reportes,
  lectura de usuarios por Coordinación, acceso a catálogos con rol desconocido y
  modificación de superusuario. El error es la reserva en sábado.
- `manage.py check`: correcto. `makemigrations --check --dry-run`: sin diferencias.
- Diagnósticos adicionales, en base de pruebas aislada: login SOLICITANTE rechazado,
  ausencia de estados iniciales y stock consecutivo incorrecto, como se detalla arriba.
- Frontend: dependencias instaladas en su ubicación nueva y compilación Vite correcta.
  Oxlint no encontró archivos en este worktree; no se declara el lint como aprobado.
- No se ejecutó la suite nueva contra PostgreSQL: el servidor local estaba apagado.
  Las 72 pruebas aprobadas de la revisión anterior no validan esta integración nueva.
- No se modificaron datos de la base de desarrollo ni código del frontend.
