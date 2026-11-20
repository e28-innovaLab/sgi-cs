import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useStore } from '../store.jsx';
import { DIAS } from '../data/mocks.js';
import { opciones, ocupacionDia } from '../logic/disponibilidad.js';
import { rango } from '../logic/formato.js';
import Badge from '../components/badge.jsx';
import Button from '../components/button.jsx';
import Aviso from '../components/aviso.jsx';
import Modal from '../components/modal.jsx';
import BarraDia from '../components/barradia.jsx';

export default function Pedidos() {
  const { state, dispatch, flash } = useStore(), loc = useLocation(), nav = useNavigate();
  const lista = state.pedidos;
  const [sel, setSel] = useState(loc.state?.sel || lista.find(p => p.estado === 'Por asignar')?.id);
  const [elegido, setElegido] = useState(null), [confirmar, setConfirmar] = useState(false), [error, setError] = useState(false);
  const p = lista.find(x => x.id === sel);
  const ops = p ? opciones(p, state) : [], op = ops.find(o => o.sp.id === elegido);
  const reservar = () => {
    // Reemplazar por POST /reservas. Si falla: setError(true) sin perder los datos.
    dispatch({ type: 'reservar', pedidoId: p.id, spId: op.sp.id, traslados: op.faltantes });
    setConfirmar(false); setElegido(null);
    flash('Reserva confirmada en ' + op.sp.nombre + '.', { label: 'Deshacer', fn: () => { dispatch({ type: 'deshacerReserva', pedidoId: p.id }); flash('Listo: el pedido volvió a Por asignar.'); } });
  };
  return (
    <div className="split">
      <section className="card lista" aria-label="Bandeja de pedidos">
        {lista.map(x => (
          <button key={x.id} className={'fila fila-btn' + (x.id === sel ? ' sel' : '')} onClick={() => { setSel(x.id); setElegido(null); }}>
            <span><strong>{x.titulo}</strong><span className="muted">{x.sol} · {x.canal}</span></span>
            <Badge tono={x.estado === 'Confirmado' ? 'ok' : 'info'}>{x.estado}</Badge>
          </button>
        ))}
      </section>
      {p && (
        <section className="card detalle">
          <h2>{p.titulo}</h2>
          <p className="muted">{DIAS[p.dia]} {rango(p.ini, p.fin)} · {p.cupo} personas · {p.resp}{p.req?.length ? ' · ' + p.req.map(r => r.cant + ' ' + r.n.toLowerCase()).join(', ') : ''}</p>
          {p.estado === 'Confirmado' ? (
            <Aviso tono="ok" titulo="Reserva confirmada" accion={<Button variant="secundario" size="sm" onClick={() => nav('/calendario')}>Ver en calendario</Button>}>El pedido ya tiene espacio.</Aviso>
          ) : (
            <>
              <h3>Espacios disponibles · elegí uno</h3>
              {ops.map(o => (
                <div key={o.sp.id} className={'opcion' + (o.sp.id === elegido ? ' sel' : '') + (o.conflictos.length ? ' bloq' : '')}>
                  <div className="opcion-head"><strong>{o.sp.nombre}</strong><span className="muted">Cupo {o.sp.cap} · Piso {o.sp.piso}</span>
                    {o.conflictos.length ? <Badge tono="err">Conflicto</Badge> : o.avisos.length ? <Badge tono="warn">Con avisos</Badge> : <Badge tono="ok">Disponible</Badge>}</div>
                  <BarraDia bloques={ocupacionDia(o.sp.id, p.dia, state.actividades)} nuevo={p} />
                  {o.conflictos.map((c, i) => <p key={i} className="txt-err">{c}</p>)}
                  {o.avisos.map((c, i) => <p key={i} className="txt-warn">{c}</p>)}
                  {o.faltantes.filter(x => x.desdeDeposito).map((x, i) => <p key={i} className="muted">Se suman {x.desdeDeposito} {x.n.toLowerCase()} desde el depósito.</p>)}
                  {!o.conflictos.length && <Button size="sm" variant={o.sp.id === elegido ? 'primario' : 'secundario'} onClick={() => setElegido(o.sp.id)}>{o.sp.id === elegido ? 'Elegido' : 'Elegir este espacio'}</Button>}
                </div>
              ))}
              {op && <Button onClick={() => setConfirmar(true)}>Confirmar reserva</Button>}
            </>
          )}
        </section>
      )}
      {confirmar && op && (
        <Modal titulo="Confirmar reserva" onClose={() => setConfirmar(false)} ancho={560}
          pie={<><Button variant="neutro" onClick={() => setConfirmar(false)}>Volver</Button><Button onClick={reservar}>{op.avisos.length ? 'Sí, confirmar igual' : 'Sí, confirmar reserva'}</Button></>}>
          {error && <Aviso tono="error" titulo="No pudimos guardar la reserva">Tus datos siguen acá. Probá de nuevo.</Aviso>}
          {op.avisos.length > 0 && <Aviso tono="warn" titulo="Este espacio tiene avisos">{op.avisos.join(' ')}</Aviso>}
          <dl className="resumen">
            <dt>Actividad</dt><dd>{p.titulo}</dd><dt>Espacio</dt><dd>{op.sp.nombre}</dd><dt>Día y horario</dt><dd>{DIAS[p.dia]} {rango(p.ini, p.fin)}</dd><dt>Personas</dt><dd>{p.cupo}</dd>
            {op.faltantes.length > 0 && <><dt>Equipamiento</dt><dd>{op.faltantes.map(x => x.desdeDeposito + ' ' + x.n.toLowerCase() + ' desde el depósito').join(', ')}</dd></>}
          </dl>
        </Modal>
      )}
    </div>
  );
}
