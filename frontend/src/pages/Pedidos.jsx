import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Badge from '../components/badge.jsx';
import Aviso from '../components/aviso.jsx';
import {
  listarReservas,
  listarAulasDisponibles,
  asignarAulasReserva,
  quitarAulaReserva,
} from '../api/reservas';


export default function Pedidos() {
  const loc = useLocation();

  const [lista, setLista] = useState([]);
  const [sel, setSel] = useState(loc.state?.sel || null);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState('');
  const [aulasDisponibles, setAulasDisponibles] = useState([]);
  const [cargandoAulas, setCargandoAulas] = useState(false);
  const [errorAulas, setErrorAulas] = useState('');
  const [aulasElegidas, setAulasElegidas] = useState([]);

  useEffect(() => {
    async function cargarReservas() {
      setCargando(true);
      setErrorCarga('');

      try {
        const respuesta = await listarReservas();
        const reservas = respuesta.results ?? respuesta;

        // En Pedidos solamente mostramos reservas pendientes.
        const reservasPendientes = reservas.filter(
          reserva => reserva.estado === 'Pendiente'
        );

        setLista(reservasPendientes);

        if (reservasPendientes.length > 0) {
          setSel(actual =>
            reservasPendientes.some(reserva => reserva.id_reserva === actual)
              ? actual
              : reservasPendientes[0].id_reserva
          );
        } else {
          setSel(null);
        }
      } catch (error) {
        setErrorCarga(error.message);
      } finally {
        setCargando(false);
      }
    }

    cargarReservas();
  }, []);

  useEffect(() => {
    async function cargarAulas() {
      if (!sel) {
        setAulasDisponibles([]);
        return;
      }

      const reserva = lista.find(
        reserva => reserva.id_reserva === sel
      );

      if (!reserva) return;

      setCargandoAulas(true);
      setErrorAulas('');
      setAulasElegidas([]);

      try {
        const aulas = await listarAulasDisponibles(
          reserva.fecha_reserva,
          reserva.horario_inicio,
          reserva.horario_fin
        );

        setAulasDisponibles(aulas);
      } catch (error) {
        setErrorAulas(error.message);
        setAulasDisponibles([]);
      } finally {
        setCargandoAulas(false);
      }
    }

    cargarAulas();
  }, [sel, lista]);


      async function quitarAula(aulaId) {
        setCargandoAulas(true);
        setErrorAulas('');

        try {
          await quitarAulaReserva(sel, aulaId);

          const respuesta = await listarReservas();
          const reservas = respuesta.results ?? respuesta;
          
          const reservasPendientes = reservas.filter(
            reserva => reserva.estado === 'Pendiente'
          );

          setLista(reservasPendientes);

          if (!reservasPendientes.some(reserva => reserva.id_reserva === sel)) {
            setSel(reservasPendientes[0]?.id_reserva ?? null);
          }

        } catch (error) {
          setErrorAulas(error.message);
        } finally {
          setCargandoAulas(false);
        }
      }

  const p = lista.find(reserva => reserva.id_reserva === sel);
  async function asignarAulas() {
    if (!sel || aulasElegidas.length === 0) {
      setErrorAulas('Seleccioná al menos un aula.');
      return;
    }

    setCargandoAulas(true);
    setErrorAulas('');

    try {
      await asignarAulasReserva(sel, aulasElegidas);

      const respuesta = await listarReservas();
      const reservas = respuesta.results ?? respuesta;

      const reservasPendientes = reservas.filter(
        reserva => reserva.estado === 'Pendiente'
      );

      setLista(reservasPendientes);

      if (!reservasPendientes.some(reserva => reserva.id_reserva === sel)) {
        setSel(reservasPendientes[0]?.id_reserva ?? null);
      }

      setAulasElegidas([]);
      setErrorAulas('');
    } catch (error) {
      setErrorAulas(error.message);
    } finally {
      setCargandoAulas(false);
    }
  }

  return (
    <div className="split">
      <section className="card lista" aria-label="Bandeja de reservas">
        {cargando && <p>Cargando reservas...</p>}

        {errorCarga && (
          <Aviso
            tono="error"
            titulo="No se pudieron cargar las reservas"
          >
            {errorCarga}
          </Aviso>
        )}

        {!cargando && !errorCarga && lista.length === 0 && (
          <p className="muted">No hay reservas pendientes para gestionar.</p>
        )}

        {!cargando && !errorCarga && lista.map(reserva => (
          <button
            key={reserva.id_reserva}
            className={'fila fila-btn' + (
              reserva.id_reserva === sel ? ' sel' : ''
            )}
            onClick={() => {
              setSel(reserva.id_reserva)
            }}
          >
            <span>
              <strong>{reserva.actividad_nombre}</strong>
              <span className="muted">
                {new Date(
                  reserva.fecha_reserva + 'T12:00:00'
                ).toLocaleDateString('es-AR')}
                {' · '}
                {reserva.horario_inicio.slice(0, 5)}
                {' - '}
                {reserva.horario_fin.slice(0, 5)}
              </span>
            </span>

            <Badge
              tono={reserva.estado === 'Confirmada' ? 'ok' : 'info'}
            >
              {reserva.estado || 'Sin estado'}
            </Badge>
          </button>
        ))}
      </section>

      {p && (
        <section className="card detalle">
          <h2>{p.actividad_nombre}</h2>

          <p className="muted">
            {new Date(
              p.fecha_reserva + 'T12:00:00'
            ).toLocaleDateString('es-AR')}
            {' · '}
            {p.horario_inicio.slice(0, 5)}
            {' - '}
            {p.horario_fin.slice(0, 5)}
          </p>

          <p>
            <strong>Estado:</strong> {p.estado || 'Sin estado'}
          </p>

          {p.detalle && (
            <p>
              <strong>Detalle:</strong> {p.detalle}
            </p>
          )}

          {p.cod_reunion && (
            <p>
              <strong>Código de reunión:</strong> {p.cod_reunion}
            </p>
          )}

          <h3>Aulas asignadas</h3>

          {p.aulas.length === 0 ? (
            <p className="muted">
              Esta reserva todavía no tiene aulas asignadas.
            </p>
          ) : (
            <ul>
              {p.aulas.map(aula => (
                <li key={aula.id}>
                  {aula.nombre} — Capacidad: {aula.capacidad}

                  <button
                    type="button"
                    onClick={() => quitarAula(aula.id)}
                    disabled={cargandoAulas}
                  >
                    Quitar
                  </button>
                </li>
              ))}
            </ul>
            )}

          <h3>Aulas disponibles</h3>

          {cargandoAulas && <p>Cargando aulas disponibles...</p>}

          {errorAulas && (
            <Aviso tono="error" titulo="No se pudieron gestionar las aulas">
              {errorAulas}
            </Aviso>
          )}

          {!cargandoAulas && !errorAulas && aulasDisponibles.length === 0 && (
            <p className="muted">
            No hay aulas disponibles para esta fecha y horario.
          </p>
          )}

          {!cargandoAulas && aulasDisponibles.map(aula => (
            <label key={aula.id} className="fila">
              <input
                type="checkbox"
                checked={aulasElegidas.includes(aula.id)}
                onChange={event => {
                  setAulasElegidas(actual =>
                    event.target.checked
                      ? [...actual, aula.id]
                      : actual.filter(id => id !== aula.id)
                  );
                }}
              />
              <span>
                <strong>{aula.nombre}</strong>
                <span className="muted"> — Capacidad: {aula.capacidad}</span>
              </span>
            </label>
          ))}

          {aulasElegidas.length > 0 && (
            <button
              type="button"
              className="btn"
              onClick={asignarAulas}
              disabled={cargandoAulas}
            >
              {cargandoAulas ? 'Asignando...' : 'Asignar aulas'}
            </button>
          )}
        </section>
      )}

      {!p && !cargando && !errorCarga && lista.length === 0 && (
        <section className="card detalle">
          <h2>Sin reservas pendientes</h2>
          <p className="muted">
            Cuando haya nuevas reservas pendientes, aparecerán aquí
            para que puedas gestionar sus aulas.
          </p>
        </section>
      )}

    </div>
  );
}
