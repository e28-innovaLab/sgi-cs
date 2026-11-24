
import { FERIADOS } from '../data/mocks.js';

export const NOMBRES_CAMPO = {
  titulo: 'Nombre de la actividad',
  sol: 'Solicitante',
  dia: 'Día',
  fecha: 'Fecha',
  hora: 'Horario',
  cupo: 'Cantidad de personas',
  resp: 'Responsable'
};

export function validarSolicitud(f, capMax) {
  const err = {};

  if (!String(f.titulo ?? '').trim()) {
    err.titulo = 'Escribí el nombre de la actividad.';
  }

  if (!f.sol) {
    err.sol = 'Elegí un área.';
  }

  // Validación de fecha para el formulario actual.
  if (f.fecha !== undefined) {
    if (!f.fecha) {
      err.fecha = 'Seleccioná una fecha.';
    } else {
      const fechaSeleccionada = new Date(f.fecha + 'T12:00:00');

      if (Number.isNaN(fechaSeleccionada.getTime())) {
        err.fecha = 'La fecha seleccionada no es válida.';
      } else {
        const diaSemana = fechaSeleccionada.getDay();

        if (diaSemana === 0 || diaSemana === 6) {
          err.fecha = 'Solo se pueden registrar actividades de lunes a viernes.';
        } else if (FERIADOS.includes(f.fecha)) {
          err.fecha = 'No se pueden registrar actividades en días feriados.';
        }
      }
    }
  } else if (f.dia === '') {
    // Compatibilidad con formularios anteriores.
    err.dia = 'Elegí un día.';
  }

  if (!f.cupo || Number(f.cupo) <= 0) {
    err.cupo = 'Escribí una cantidad de personas válida.';
  } else if (
    Number.isFinite(Number(capMax)) &&
    Number(capMax) > 0 &&
    Number(f.cupo) > Number(capMax)
  ) {
    err.cupo = 'El cupo supera la capacidad máxima disponible.';
  }

  if (!String(f.resp ?? '').trim()) {
    err.resp = 'Escribí el responsable.';
  }

  return err;
}

export function validarPresentes(val, insc) {
  const n = Number(val);

  if (val.trim() === '' || isNaN(n)) {
    return 'Escribí un número.';
  }

  if (n < 0 || n > insc) {
    return `Debe estar entre 0 y ${insc}.`;
  }

  return '';
}

export function validarFilaAsistente(r) {
  if (!r[0] || !r[1]) {
    return 'Falta nombre o apellido.';
  }

  if (!r[2] || r[2].length < 7) {
    return 'DNI inválido.';
  }

  return '';
}
