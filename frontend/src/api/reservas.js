import { apiFetch } from './client';

// Obtener todas las reservas.
export function listarReservas() {
  return apiFetch('/reservas/');
}

// Crear una nueva reserva.
export function crearReserva(datos) {
  return apiFetch('/reservas/', {
    method: 'POST',
    body: JSON.stringify(datos),
  });
}

// Obtener una reserva específica.
export function obtenerReserva(id) {
  return apiFetch(`/reservas/${id}/`);
}

// Consultar aulas disponibles para una fecha y horario.
export function listarAulasDisponibles(fecha, horaInicio, horaFin) {
  const parametros = new URLSearchParams({
    fecha,
    hora_inicio: horaInicio,
    hora_fin: horaFin,
  });

  return apiFetch(`/aulas-disponibles/?${parametros.toString()}`);
}

// Asignar aulas a una reserva.
export function asignarAulasReserva(id, aulasIds) {
  return apiFetch(`/reservas/${id}/asignar-aulas/`, {
    method: 'POST',
    body: JSON.stringify({
      aulas_ids: aulasIds,
    }),
  });
}

// Quitar un aula de una reserva.
export function quitarAulaReserva(id, aulaId) {
  return apiFetch(`/reservas/${id}/quitar-aula/`, {
    method: 'DELETE',
    body: JSON.stringify({
      aula_id: aulaId,
    }),
  });
}
