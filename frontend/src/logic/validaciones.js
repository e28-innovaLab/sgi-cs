export const NOMBRES_CAMPO = { titulo: 'Nombre de la actividad', sol: 'Solicitante', dia: 'Día', hora: 'Horario', cupo: 'Cantidad de personas', resp: 'Responsable' };

export function validarSolicitud(f, capMax) {
  const err = {};
  if (!f.titulo.trim()) err.titulo = 'Escribí el nombre.';
  if (!f.sol) err.sol = 'Elegí un área.';
  if (f.dia === '') err.dia = 'Elegí un día.';
  if (!f.cupo || Number(f.cupo) <= 0) err.cupo = 'Escribí un cupo válido.';
  else if (Number(f.cupo) > capMax) err.hora = 'El cupo supera el máximo disponible.';
  if (!f.resp.trim()) err.resp = 'Escribí el responsable.';
  return err;
}

export function validarPresentes(val, insc) {
  const n = Number(val);
  if (val.trim() === '' || isNaN(n)) return 'Escribí un número.';
  if (n < 0 || n > insc) return `Debe estar entre 0 y ${insc}.`;
  return '';
}

export function validarFilaAsistente(r) {
  if (!r[0] || !r[1]) return 'Falta nombre o apellido.';
  if (!r[2] || r[2].length < 7) return 'DNI inválido.';
  return '';
}