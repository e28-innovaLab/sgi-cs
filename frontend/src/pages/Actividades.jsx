import { useEffect, useState, useRef } from 'react';
import {
  listarActividades,
  crearActividad,
  actualizarActividad,
  eliminarActividad,
} from '../api/actividades.js';

const TIPOS_ACTIVIDAD = [
  { value: 'CURSO', label: 'Curso' },
  { value: 'PRACTICA', label: 'Práctica' },
  { value: 'WORKSHOP', label: 'Workshop' },
  { value: 'CAPACITACION', label: 'Capacitación' },
  { value: 'LABORATORIO', label: 'Laboratorio' },
  { value: 'OTRA', label: 'Otra' },
];

const formularioInicial = {
  nombre: '',
  tipo: 'CURSO',
  fecha_estimada: '',
  horario_inicio_estimado: '',
  horario_fin_estimado: '',
  participantes_estimados: 1,
  requerimiento_espacio: '',
  equipamiento_necesario: '',
};

export default function Actividades() {
  const [actividades, setActividades] = useState([]);
  const [formulario, setFormulario] = useState(formularioInicial);
  const [actividadEditando, setActividadEditando] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const formularioRef = useRef(null);

  async function cargarActividades() {
    setCargando(true);
    setError('');

    try {
      const respuesta = await listarActividades();
      setActividades(respuesta.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    cargarActividades();
  }, []);

  function manejarCambio(event) {
    const { name, value } = event.target;

    setFormulario(actual => ({
      ...actual,
      [name]: name === 'participantes_estimados'
        ? Number(value)
        : value,
    }));
  }

  function iniciarEdicion(actividad) {
    console.log('Actividad seleccionada:', actividad);
    setActividadEditando(actividad.id_actividad);

    setFormulario({
      nombre: actividad.nombre,
      tipo: actividad.tipo,
      fecha_estimada: actividad.fecha_estimada,
      horario_inicio_estimado: actividad.horario_inicio_estimado?.slice(0, 5) || '',
      horario_fin_estimado: actividad.horario_fin_estimado?.slice(0, 5) || '',
      participantes_estimados: actividad.participantes_estimados,
      requerimiento_espacio: actividad.requerimiento_espacio || '',
      equipamiento_necesario: actividad.equipamiento_necesario || '',
    });

    setError('');
    setMensaje('');
    setTimeout(() => {
      formularioRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 100);
  }

  async function manejarEliminar(actividad) {
    const confirmar = window.confirm(
      `¿Estás seguro de que querés eliminar la actividad "${actividad.nombre}"?`
    );

    if (!confirmar) return;

    setError('');
    setMensaje('');

    try {
      await eliminarActividad(actividad.id_actividad);

      if (actividadEditando === actividad.id_actividad) {
        setActividadEditando(null);
        setFormulario(formularioInicial);
      }

      setMensaje('Actividad eliminada correctamente.');
      await cargarActividades();
    } catch (err) {
      setError(err.message);
    }
  }

  async function manejarEnvio(event) {
    event.preventDefault();
    setError('');
    setMensaje('');

    if (
      formulario.horario_fin_estimado <=
      formulario.horario_inicio_estimado
    ) {
      setError('La hora de finalización debe ser posterior a la de inicio.');
      return;
    }

    setGuardando(true);

    try {
      if (actividadEditando !== null) {
        await actualizarActividad(actividadEditando, formulario);
        setMensaje('Actividad actualizada correctamente.');
        setActividadEditando(null);
      } else {
        await crearActividad(formulario);
        setMensaje('Actividad creada correctamente.');
      }

      setFormulario(formularioInicial);
      await cargarActividades();
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="actividades-page">

      {/* Formulario */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>{actividadEditando !== null ? 'Editar actividad' : 'Nueva actividad'}</h3>
            <p>Completá los datos para registrar una actividad.</p>
          </div>
        </div>

        <form ref={formularioRef} className="activity-form" onSubmit={manejarEnvio}>
          <div className="activity-fields">

            <div className="form-group">
              <label htmlFor="nombre">Nombre de la actividad</label>
              <input
                id="nombre"
                name="nombre"
                value={formulario.nombre}
                onChange={manejarCambio}
                required
                maxLength={200}
                placeholder="Ej. Curso de programación"
              />
            </div>

            <div className="form-group">
              <label htmlFor="tipo">Tipo de actividad</label>
              <select
                id="tipo"
                name="tipo"
                value={formulario.tipo}
                onChange={manejarCambio}
                required
              >
                {TIPOS_ACTIVIDAD.map(tipo => (
                  <option key={tipo.value} value={tipo.value}>
                    {tipo.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="fecha_estimada">Fecha estimada</label>
              <input
                id="fecha_estimada"
                name="fecha_estimada"
                type="date"
                value={formulario.fecha_estimada}
                onChange={manejarCambio}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="participantes_estimados">
                Cantidad estimada de participantes
              </label>
              <input
                id="participantes_estimados"
                name="participantes_estimados"
                type="number"
                min="1"
                value={formulario.participantes_estimados}
                onChange={manejarCambio}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="horario_inicio_estimado">Hora de inicio</label>
              <input
                id="horario_inicio_estimado"
                name="horario_inicio_estimado"
                type="time"
                value={formulario.horario_inicio_estimado}
                onChange={manejarCambio}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="horario_fin_estimado">Hora de finalización</label>
              <input
                id="horario_fin_estimado"
                name="horario_fin_estimado"
                type="time"
                value={formulario.horario_fin_estimado}
                onChange={manejarCambio}
                required
              />
            </div>

            <div className="form-group activity-field-full">
              <label htmlFor="requerimiento_espacio">
                Requerimiento de espacio
              </label>
              <textarea
                id="requerimiento_espacio"
                name="requerimiento_espacio"
                value={formulario.requerimiento_espacio}
                onChange={manejarCambio}
                placeholder="Describí las características del espacio necesario..."
              />
            </div>

            <div className="form-group activity-field-full">
              <label htmlFor="equipamiento_necesario">
                Equipamiento necesario
              </label>
              <textarea
                id="equipamiento_necesario"
                name="equipamiento_necesario"
                value={formulario.equipamiento_necesario}
                onChange={manejarCambio}
                placeholder="Indicá qué equipamiento se necesitará..."
              />
            </div>

          </div>

          {error && (
            <p className="activity-message activity-error" role="alert">
              {error}
            </p>
          )}

          {mensaje && (
            <p className="activity-message activity-success">
              {mensaje}
            </p>
          )}

          <div className="activity-form-actions">
            <button type="submit" disabled={guardando}>
              {guardando
                ? 'Guardando...'
                : actividadEditando !== null
                  ? 'Guardar cambios'
                  : 'Crear actividad'}
            </button>
            {actividadEditando !== null && (
              <button
                type="button"
                onClick={() => {
                  setActividadEditando(null);
                  setFormulario(formularioInicial);
                  setError('');
                  setMensaje('');
                }}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Listado */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Actividades registradas</h3>
            <p>Consultá las actividades creadas en el sistema.</p>
          </div>

          <span className="pedidos-total">
            {actividades.length} actividades
          </span>
        </div>

        {cargando ? (
          <p>Cargando actividades...</p>
        ) : actividades.length === 0 ? (
          <p>No hay actividades registradas.</p>
        ) : (
          <div className="activity-list">
            {actividades.map(actividad => (
              <article
                className="activity-card"
                key={actividad.id_actividad}
              >
                <div className="activity-card-header">
                  <div>
                    <h4>{actividad.nombre}</h4>
                    <span className="activity-type">
                      {TIPOS_ACTIVIDAD.find(
                        tipo => tipo.value === actividad.tipo
                      )?.label || actividad.tipo}
                    </span>
                  </div>
                  <div className="activity-card-actions">
                    <button
                      type="button"
                      className="activity-edit-button"
                      onClick={() => iniciarEdicion(actividad)}
                    >
                      Editar
                    </button>

                    <button
                      type="button"
                      className="activity-delete-button"
                      onClick={() => manejarEliminar(actividad)}
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
                <div className="activity-card-details">
                  <div>
                    <span>Fecha</span>
                    <strong>{actividad.fecha_estimada}</strong>
                  </div>

                  <div>
                    <span>Horario</span>
                    <strong>
                      {actividad.horario_inicio_estimado?.slice(0, 5)}
                      {' a '}
                      {actividad.horario_fin_estimado?.slice(0, 5)}
                    </strong>
                  </div>

                  <div>
                    <span>Participantes estimados</span>
                    <strong>{actividad.participantes_estimados}</strong>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

    </div>
  );
}
