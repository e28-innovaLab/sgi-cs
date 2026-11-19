// Reglas de la interfaz. Backend debe aplicar las mismas (ver README del handoff, "Reglas de negocio").
import { FERIADOS } from '../data/mocks.js';
import { seSuperpone, rango } from './formato.js';

const libres = (equipos, n) => equipos.filter(e => e.n === n && !e.fijo && e.ubic === 'Depósito' && e.estado === 'Disponible').reduce((s, e) => s + e.cant, 0);
const enEspacio = (equipos, sp, n) => equipos.filter(e => e.n === n && e.ubic === sp.nombre && e.estado === 'Disponible').reduce((s, e) => s + e.cant, 0);

// Devuelve { conflictos: [], avisos: [], faltantes: [] } para un pedido en un espacio.
export function evaluar(pedido, sp, { actividades, equipos }) {
  const conflictos = [], avisos = [], faltantes = [];
  if (FERIADOS.includes(pedido.dia)) conflictos.push('Es feriado: no se reserva ese día.');
  if (sp.estado === 'Mantenimiento') conflictos.push(sp.nombre + ' está en mantenimiento' + (sp.hasta ? ' hasta el ' + sp.hasta : '') + '.');
  if (pedido.cupo > sp.cap) conflictos.push(sp.nombre + ' tiene capacidad para ' + sp.cap + '.');
  const choque = actividades.find(a => !a.cancelada && a.sp === sp.id && seSuperpone(a, pedido));
  if (choque) conflictos.push('Se superpone con "' + choque.titulo + '" (' + rango(choque.ini, choque.fin) + ').');
  (pedido.req || []).forEach(r => {
    const hay = enEspacio(equipos, sp, r.n), dep = libres(equipos, r.n), falta = Math.max(0, r.cant - hay);
    const crit = equipos.some(e => e.n === r.n && e.critico);
    if (falta === 0) return;
    if (dep >= falta) faltantes.push({ n: r.n, falta, desdeDeposito: falta });
    else if (crit) conflictos.push('Falta ' + r.n.toLowerCase() + ' (equipo crítico).');
    else { faltantes.push({ n: r.n, falta, desdeDeposito: dep }); avisos.push('Faltan ' + (falta - dep) + ' ' + r.n.toLowerCase() + ': queda como recurso pendiente.'); }
  });
  const sim = sp.sims.reduce((s, x) => s + x.c, 0);
  if (sim && sim < pedido.cupo) avisos.push(sim + ' simuladores para ' + pedido.cupo + ' personas: se trabaja por turnos.');
  return { conflictos, avisos, faltantes };
}

// Opciones ordenadas: primero sin conflictos, luego el cupo más ajustado. La persona elige.
export function opciones(pedido, ctx) {
  return ctx.espacios.map(sp => ({ sp, ...evaluar(pedido, sp, ctx) }))
    .sort((a, b) => (a.conflictos.length > 0) - (b.conflictos.length > 0) || (a.sp.cap - pedido.cupo) - (b.sp.cap - pedido.cupo));
}

// Bloques ocupados del día para la barra de disponibilidad (8 a 20 h).
export const ocupacionDia = (spId, dia, actividades) => actividades.filter(a => !a.cancelada && a.sp === spId && a.dia === dia).map(a => ({ ini: a.ini, fin: a.fin, titulo: a.titulo }));
