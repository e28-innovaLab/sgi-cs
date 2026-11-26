import { apiFetch } from './client';

export function listarActividades() {
  return apiFetch('/actividades/');
}

export function crearActividad(datos) {
  return apiFetch('/actividades/', {
    method: 'POST',
    body: JSON.stringify(datos),
  });
}

export function obtenerActividad(id) {
  return apiFetch(`/actividades/${id}/`);
}

export function actualizarActividad(id, datos) {
  return apiFetch(`/actividades/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(datos),
  });
}

export function eliminarActividad(id) {
  return apiFetch(`/actividades/${id}/`, {
    method: 'DELETE',
  });
}