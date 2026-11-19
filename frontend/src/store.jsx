import { createContext, useContext, useReducer, useRef, useCallback } from 'react';
import { ESPACIOS, EQUIPOS, ACTIVIDADES, PEDIDOS, USUARIOS } from './data/mocks.js';

const Ctx = createContext(null);
const inicial = { sesion: null, espacios: ESPACIOS, equipos: EQUIPOS, actividades: ACTIVIDADES, pedidos: PEDIDOS, usuarios: USUARIOS, toast: null, modalSolicitud: false };

function reducer(s, a) {
  switch (a.type) {
    case 'login': return { ...s, sesion: a.sesion };
    case 'logout': return { ...s, sesion: null };
    case 'rol': return { ...s, sesion: { ...s.sesion, rol: a.rol } };
    case 'toast': return { ...s, toast: a.toast };
    case 'modalSolicitud': return { ...s, modalSolicitud: a.open };
    case 'pedidoNuevo': return { ...s, pedidos: [a.pedido, ...s.pedidos] };
    case 'reservar': {
      const p = s.pedidos.find(x => x.id === a.pedidoId), id = 'a' + Date.now();
      const act = { id, titulo: p.titulo, tipo: p.tipo, sol: p.sol, sp: a.spId, dia: p.dia, ini: p.ini, fin: p.fin, insc: p.cupo, resp: p.resp, codigo: '', personas: [], reg: false, cancelada: false, pedidoId: p.id, traslados: a.traslados || [] };
      return { ...s, actividades: [...s.actividades, act], pedidos: s.pedidos.map(x => x.id === p.id ? { ...x, estado: 'Confirmado', actId: id } : x) };
    }
    case 'deshacerReserva': {
      const p = s.pedidos.find(x => x.id === a.pedidoId);
      return { ...s, actividades: s.actividades.filter(x => x.id !== p.actId), pedidos: s.pedidos.map(x => x.id === p.id ? { ...x, estado: 'Por asignar', actId: null } : x) };
    }
    case 'actividad': return { ...s, actividades: s.actividades.map(x => x.id === a.id ? { ...x, ...a.cambios } : x) };
    default: return s;
  }
}

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, inicial);
  const t = useRef();
  // Toast: 2,6 s; con acción (Deshacer) 8 s.
  const flash = useCallback((texto, accion) => {
    clearTimeout(t.current);
    dispatch({ type: 'toast', toast: { texto, accion } });
    t.current = setTimeout(() => dispatch({ type: 'toast', toast: null }), accion ? 8000 : 2600);
  }, []);
  return <Ctx.Provider value={{ state, dispatch, flash }}>{children}</Ctx.Provider>;
}
export const useStore = () => useContext(Ctx);
