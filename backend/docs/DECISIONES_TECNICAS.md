# Decisiones técnicas – Etapa 3: Operaciones de reservas

Este documento resume las decisiones técnicas implementadas en el backend para gestionar las operaciones de reservas.

## 1. Modelado de las reservas

- Una reserva está asociada a una actividad mediante una relación con `Actividad`.
- Una actividad registra su nombre, tipo, responsable, fecha, horario estimado, cantidad de participantes estimado y requerimientos de espacio o equipamiento. Los atributos son estimados porque los valores reales serán los valores de que se registren en la entidad Reserva.
- Una reserva almacena la fecha, horario de inicio y fin, detalle, estado y código de reunión.
- Los horarios se almacenan como campos de hora, separados de la fecha.
- Una reserva puede tener varios usuarios asociados y varios participantes.


## 2. Estados de reserva

Se definieron cinco estados:

- `Pendiente`
- `Confirmada`
- `Cancelada`
- `Rechazada`
- `Finalizada`

Las reservas pendientes y confirmadas son las que se consideran al calcular la disponibilidad de aulas y equipamiento.

Las operaciones de confirmación y rechazo se realizan sobre reservas pendientes. Una reserva pendiente puede cancelarse; una confirmada puede cancelarse únicamente antes de su inicio.

Los estados `Cancelada`, `Rechazada` y `Finalizada` se consideran estados terminales. Una vez que una reserva alcanza cualquiera de ellos, no se permite modificar su estado a otro diferente. Esta regla se valida en el modelo `Reserva` al guardar los cambios.

También existe un servicio para actualizar automáticamente las reservas vencidas:

- Las pendientes cuyo horario de inicio ya pasó se cancelan.
- Las confirmadas cuyo horario de finalización ya pasó se finalizan.


## 3. Usuarios y solicitante

La relación entre usuarios y reservas se implementa mediante el modelo intermedio `UsuarioPorReserva`.

Este modelo permite:

- Asociar varios usuarios a una reserva.
- Identificar cuál de los usuarios es el solicitante.
- Evitar que un mismo usuario se asocie más de una vez a una misma reserva.
- Limitar a uno la cantidad de usuarios marcados como solicitantes mediante una restricción de base de datos.

Al confirmar una reserva, el servicio verifica que exista exactamente un solicitante. La restricción de base de datos garantiza que no haya más de uno, mientras que la validación del servicio comprueba que haya uno.

La asociación, modificación del solicitante y eliminación de usuarios se permiten únicamente mientras la reserva está pendiente. El solicitante actual no puede eliminarse sin asignar primero otro.


## 4. Disponibilidad y asignación de aulas

El servicio `obtener_aulas_disponibles` obtiene las aulas que no están ocupadas durante el horario solicitado.

Para determinar si existe un conflicto, se consideran las reservas de la misma fecha que estén pendientes o confirmadas y cuyos horarios se superpongan.

La superposición se comprueba mediante estas condiciones:

- El inicio de una reserva debe ser anterior al fin de la otra.
- El fin de una reserva debe ser posterior al inicio de la otra.

Por lo tanto, dos reservas cuyos horarios solamente coinciden en el límite no se consideran superpuestas.

El servicio `asignar_aulas_reserva`:

- Exige que se asigne al menos un aula.
- Verifica que las aulas existan y estén disponibles.
- Comprueba que no haya otra reserva pendiente o confirmada que ocupe esas aulas en un horario superpuesto.
- Reemplaza las asociaciones anteriores por las nuevas.

La asignación se ejecuta dentro de una transacción y utiliza bloqueos de filas para reducir conflictos ante operaciones concurrentes.


## 5. Modelado y disponibilidad del equipamiento

Cada equipamiento tiene:

- Una categoría.
- Una cantidad total.
- Un estado.
- Una relación opcional con un aula.
- Una propiedad `trasladable` que determina cómo se calcula su disponibilidad.

El modelo valida que el equipamiento no trasladable tenga un aula asignada. El equipamiento trasladable no necesita estar asociado a un aula específica.

La disponibilidad se calcula de manera diferente según el tipo:

- Equipamiento trasladable: se consideran las cantidades comprometidas en otras reservas pendientes o confirmadas que coincidan en fecha y horario.
- Equipamiento no trasladable: se consideran las solicitudes de otras reservas que utilizan el aula a la que pertenece el equipamiento y que coinciden en fecha y horario.

Para calcular el stock disponible se resta del total la cantidad comprometida por otras reservas. Cuando existe una cantidad reservada se utiliza ese valor; de lo contrario, se utiliza la cantidad solicitada.

Los equipamientos que no están en estado disponible no se ofrecen como disponibles.

El servicio de solicitud de equipamiento permite crear o modificar solicitudes para reservas pendientes o confirmadas. Se verifica que la cantidad solicitada no supere el stock disponible.


## 6. Validación y confirmación de reservas

La confirmación se realiza mediante el servicio `confirmar_reserva`.

Antes de cambiar el estado a confirmada, se comprueba que:

- El usuario tenga permisos para operar sobre la reserva.
- La reserva esté pendiente.
- Exista exactamente un solicitante.
- Se haya asignado al menos un aula.
- Las aulas asignadas estén disponibles y no tengan conflictos de horario.
- Los equipamientos solicitados estén disponibles y las cantidades sean válidas.

Las operaciones de confirmación, rechazo y cancelación se ejecutan dentro de transacciones y utilizan bloqueos sobre la reserva para reducir conflictos entre operaciones simultáneas.


## 7. Participantes y asistencia

Los participantes se almacenan independientemente de las reservas y se relacionan mediante `ReservaParticipante`.

La identificación de una persona se realiza mediante la combinación de tipo y número de documento. Esta combinación es única.

El servicio `obtener_o_crear_participante` permite reutilizar un participante existente o crear uno nuevo cuando no se encuentra registrado.

La relación entre participante y reserva almacena también su rol, por ejemplo docente, ayudante docente, estudiante, observador, visita u otro.

La asistencia se registra mediante el campo `presente`, que admite tres valores:

- `True`: presente.
- `False`: ausente.
- `None`: asistencia todavía no registrada.

La actualización de asistencia se permite cuando la reserva está confirmada o finalizada.


## 8. Permisos y operaciones

Los servicios contemplan permisos diferenciados para administradores, coordinación y solicitantes.

En las operaciones de confirmación y cancelación pueden intervenir administradores, usuarios de coordinación o el solicitante de la reserva, según las reglas de cada operación.

El rechazo está reservado a administradores y usuarios de coordinación.

Las operaciones de gestión de usuarios asociados a una reserva están limitadas al estado pendiente.

En Django Admin, el campo de estado se deshabilita cuando la reserva se encuentra cancelada, rechazada o finalizada. Para las reservas nuevas, el estado inicial se establece como pendiente.


## 9. Validaciones generales

Se incorporaron validaciones para evitar datos inconsistentes, entre ellas:

- El horario de finalización debe ser posterior al horario de inicio.
- Las reservas pendientes o confirmadas no pueden tener una fecha u hora de inicio pasada al validarse.
- Una reserva cancelada, rechazada o finalizada no puede cambiar a otro estado.
- La cantidad estimada de participantes debe ser como mínimo uno.
- La cantidad solicitada de equipamiento debe ser mayor que cero.
- La cantidad crítica no puede superar la cantidad solicitada.
- La cantidad reservada no puede superar la cantidad solicitada.
- La fecha de nacimiento de un participante no puede ser futura.
- El número de documento de un participante no puede estar vacío.

La validación de estados terminales se ejecuta desde el método `clean()` del modelo `Reserva`, invocado al guardar mediante `save()`. Esta protección se aplica a las operaciones que utilizan el guardado normal del modelo; no constituye una restricción absoluta a nivel de PostgreSQL.


## 10. Uso de transacciones y bloqueos

Las operaciones que modifican recursos o el estado de una reserva utilizan transacciones mediante `transaction.atomic`.

En las operaciones correspondientes se emplea `select_for_update` para bloquear filas durante la ejecución. Esto ayuda a reducir problemas cuando dos operaciones intentan modificar o asignar los mismos recursos al mismo tiempo.

Las validaciones de disponibilidad se realizan en el backend, evitando depender exclusivamente de los controles de la interfaz.


## 11. Pruebas automatizadas

Se incorporaron pruebas para verificar el comportamiento de las operaciones de reservas, incluyendo:

- Disponibilidad y superposición de horarios.
- Exclusión de reservas canceladas y rechazadas del cálculo de disponibilidad.
- Validación de intervalos horarios.
- Protección de los estados terminales.
- Posibilidad de modificar otros datos de una reserva sin cambiar su estado terminal.
- Comportamiento de los servicios frente a reservas con estados terminales.
- Respeto de los estados terminales por parte del servicio de finalización automática.


---

Este documento describe el comportamiento identificado en los modelos, servicios, administración y pruebas revisados. No implica que todas las operaciones tengan las mismas restricciones: cada servicio aplica sus propias condiciones.

