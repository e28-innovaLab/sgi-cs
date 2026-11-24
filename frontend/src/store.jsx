
import { createContext, useContext, useReducer, useRef, useCallback } from 'react';
import { ESPACIOS, EQUIPOS, ACTIVIDADES, PEDIDOS, USUARIOS } from './data/mocks.js';

const Ctx = createContext(null);

const inicial = {
  sesion: null,
  espacios: ESPACIOS,
  equipos: EQUIPOS,
  actividades: ACTIVIDADES,
  pedidos: PEDIDOS,
  usuarios: USUARIOS,
  toast: null,
  modalSolicitud: false
};

function reducer(s, a) {
  switch (a.type) {
    case 'login':
      return { ...s, sesion: a.sesion };

    case 'logout':
      return { ...s, sesion: null };

    case 'rol':
      return { ...s, sesion: { ...s.sesion, rol: a.rol } };

    case 'toast':
      return { ...s, toast: a.toast };

    case 'modalSolicitud':
      return { ...s, modalSolicitud: a.open };

    // Crear un pedido nuevo
    case 'pedidoNuevo':
      return {
        ...s,
        pedidos: [a.pedido, ...s.pedidos]
      };

    // Confirmar la asignación de un espacio
    case 'reservar': {
      const p = s.pedidos.find(x => x.id === a.pedidoId);

      if (!p) return s;

      const id = 'a' + Date.now();

      const act = {
        id,
        pedidoId: p.id,
        titulo: p.titulo,
        tipo: p.tipo,
        canal: p.canal,
        sol: p.sol,
        sp: a.spId,

        // Conservamos fecha y día para compatibilidad
        // con actividades antiguas.
        fecha: p.fecha || null,
        dia: p.dia,

        ini: p.ini,
        fin: p.fin,
        insc: p.cupo,
        resp: p.resp,

        // Equipamiento solicitado y traslados
        req: (p.req || []).map(r => ({ ...r })),
        traslados: (a.traslados || []).map(t => ({ ...t })),

        codigo: '',
        personas: [],
        reg: false,
        cancelada: false
      };

      return {
        ...s,
        actividades: [...s.actividades, act],
        pedidos: s.pedidos.map(x =>
          x.id === p.id
            ? {
                ...x,
                estado: 'Confirmado',
                actId: id,
                motivoRechazo: ''
              }
            : x
        )
      };
    }

    // Deshacer una reserva
    case 'deshacerReserva': {
      const p = s.pedidos.find(x => x.id === a.pedidoId);

      if (!p || !p.actId) return s;

      return {
        ...s,
        actividades: s.actividades.filter(x => x.id !== p.actId),
        pedidos: s.pedidos.map(x =>
          x.id === p.id
            ? {
                ...x,
                estado: 'Por asignar',
                actId: null,
                motivoRechazo: ''
              }
            : x
        )
      };
    }

    // Rechazar un pedido sin eliminarlo del historial
    case 'rechazarPedido': {
      const p = s.pedidos.find(x => x.id === a.pedidoId);

      if (!p) return s;

      return {
        ...s,
        pedidos: s.pedidos.map(x =>
          x.id === p.id
            ? {
                ...x,
                estado: 'Rechazado',
                motivoRechazo: (a.motivo || '').trim(),
                actId: null
              }
            : x
        )
      };
    }

    // Modificar una actividad
    case 'actividad':
      return {
        ...s,
        actividades: s.actividades.map(x =>
          x.id === a.id
            ? { ...x, ...a.cambios }
            : x
        )
      };

    default:
      return s;
  }
}

export function StoreProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, inicial);
  const t = useRef();

  // Toast: 2,6 segundos; con acción (Deshacer), 8 segundos.
  const flash = useCallback((texto, accion) => {
    clearTimeout(t.current);

    dispatch({
      type: 'toast',
      toast: { texto, accion }
    });

    t.current = setTimeout(
      () => dispatch({ type: 'toast', toast: null }),
      accion ? 8000 : 2600
    );
  }, []);

  return (
    <Ctx.Provider value={{ state, dispatch, flash }}>
      {children}
    </Ctx.Provider>
  );
}

export const useStore = () => useContext(Ctx);