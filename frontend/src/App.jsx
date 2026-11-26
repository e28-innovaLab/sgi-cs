import { apiFetch } from './api/client'
import { listarActividades } from './api/actividades';
import { crearReserva, listarReservas } from './api/reservas';
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import './App.css'
import Login from './components/Login'
import Pedidos from './pages/Pedidos.jsx';
import Actividades from './pages/Actividades.jsx';
import { useStore } from './store.jsx'
import { DIAS, AREAS } from './data/mocks.js'
import Calendario from './pages/Calendario.jsx';
import { validarSolicitud } from './logic/validaciones.js';

function App() {
  const { state, dispatch } = useStore()
  const navigate = useNavigate()
  const location = useLocation()

  const [mensaje, setMensaje] = useState('')
  const [verificandoSesion, setVerificandoSesion] = useState(true)
  const [actividadesDisponibles, setActividadesDisponibles] = useState([]);
  const [cargandoActividades, setCargandoActividades] = useState(false);
  const [errorActividades, setErrorActividades] = useState('');
  const [reservasRegistradas, setReservasRegistradas] = useState([]);
  const [cargandoReservas, setCargandoReservas] = useState(false);
  const [errorReservas, setErrorReservas] = useState('');

  useEffect(() => {
    async function recuperarSesion() {
      const token = sessionStorage.getItem('token')

      if (!token) {
        setVerificandoSesion(false)
        return
      }

      try {
        const usuario = await apiFetch('/auth/me/')
        dispatch({ type: 'login', sesion: usuario })
      } catch (error) {
        sessionStorage.removeItem('token')
        dispatch({ type: 'logout' })
      } finally {
        setVerificandoSesion(false)
      }
    }

    recuperarSesion()
  }, [dispatch])


  const espacios = state.espacios
  const equipos = state.equipos
  const actividades = state.actividades
  const pedidos = state.pedidos

  const seccionActiva =
    location.pathname === '/'
      ? 'inicio'
      : location.pathname.replace('/', '')


  useEffect(() => {
    if (seccionActiva !== 'reservas') return;

    async function cargarActividades() {
      setCargandoActividades(true);
      setErrorActividades('');

      try {
        const respuesta = await listarActividades();

        setActividadesDisponibles(
          respuesta.results ?? respuesta
        );
      } catch (error) {
        setErrorActividades(error.message);
      } finally {
        setCargandoActividades(false);
      }
    }

    cargarActividades();
  }, [seccionActiva]);

  useEffect(() => {
    if (seccionActiva !== 'reservas') return;

    const cargarReservas = async () => {
      try {
        setCargandoReservas(true);
        setErrorReservas('');

        const respuesta = await listarReservas();

        setReservasRegistradas(respuesta.results ?? respuesta);
      } catch (error) {
        setErrorReservas(error.message || 'No se pudieron cargar las reservas.');
      } finally {
        setCargandoReservas(false);
      }
    };

    cargarReservas();
  }, [seccionActiva]);


  function irASeccion(seccion) {
    navigate(seccion === 'inicio' ? '/' : `/${seccion}`)
  }

 
async function agregarPedido(event) {
  event.preventDefault();

  const formulario = event.currentTarget;
  const datos = new FormData(formulario);

  const actividad = Number(datos.get('actividad'));
  const fecha = datos.get('fecha');
  const horarioInicio = datos.get('ini');
  const horarioFin = datos.get('fin');
  const detalle = datos.get('detalle').trim();
  const codReunion = datos.get('cod_reunion').trim();

  if (horarioFin <= horarioInicio) {
    setMensaje('La hora de finalización debe ser posterior a la hora de inicio.');
    return;
  }

  const reserva = {
    actividad,
    fecha_reserva: fecha,
    horario_inicio: `${horarioInicio}:00`,
    horario_fin: `${horarioFin}:00`,
    detalle,
    cod_reunion: codReunion || null,
  };

  try {
    await crearReserva(reserva);

    // Actualizar el listado con las reservas del backend.
    const respuesta = await listarReservas();
    setReservasRegistradas(respuesta.results ?? respuesta);

    formulario.reset();
    setMensaje('La reserva se registró correctamente.');
  } catch (error) {
    setMensaje(`No se pudo registrar la reserva: ${error.message}`);
  }
}

    
  const pendientes = pedidos.filter(
    pedido => pedido.estado === 'Por asignar'
  ).length

  const espaciosDisponibles = espacios.filter(
    espacio => espacio.estado === 'Disponible'
  ).length

  if (verificandoSesion) {
    return <p>Verificando sesión...</p>
  }

  if (!state.sesion) {
    return (
      <Login
        onLogin={(usuario) => dispatch({ type: 'login', sesion: usuario })}
      />
    )
  }

  return (
    <div className="app">

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <img src="/logo.jpg" alt="Logo de SIGES" />
          </div>
          <div>
            <h1>SIGES</h1>
            <span>Gestión de espacios</span>
          </div>
        </div>

        <div className="menu-label">MENÚ PRINCIPAL</div>

        <nav className="menu">

          <a
            className={`menu-item ${seccionActiva === 'inicio' ? 'active' : ''}`}
            href="/"
            onClick={event => {
              event.preventDefault()
              irASeccion('inicio')
            }}
          >
            ▦ <span>Inicio</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'dashboard' ? 'active' : ''}`}
            href="/dashboard"
            onClick={event => {
              event.preventDefault()
              irASeccion('dashboard')
            }}
          >
            ▥ <span>Dashboard</span>
          </a>
          <a
            className={`menu-item ${seccionActiva === 'actividades' ? 'active' : ''}`}
            href="/actividades"
            onClick={event => {
              event.preventDefault();
              irASeccion('actividades');
            }}
          >
            ▣ <span>Actividades</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'reservas' ? 'active' : ''}`}
            href="/reservas"
            onClick={event => {
              event.preventDefault()
              irASeccion('reservas')
            }}
          >
            ▣ <span>Reservas</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'pedidos' ? 'active' : ''}`}
            href="/pedidos"
            onClick={event => {
              event.preventDefault()
              irASeccion('pedidos')
            }}
          >
            ▤ <span>Pedidos</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'espacios' ? 'active' : ''}`}
            href="/espacios"
            onClick={event => {
              event.preventDefault()
              irASeccion('espacios')
            }}
          >
            ⌂ <span>Espacios</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'recursos' ? 'active' : ''}`}
            href="/recursos"
            onClick={event => {
              event.preventDefault()
              irASeccion('recursos')
            }}
          >
            ▤ <span>Recursos y equipos</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'calendario' ? 'active' : ''}`}
            href="/calendario"
            onClick={event => {
              event.preventDefault()
              irASeccion('calendario')
            }}
          >
            ▦ <span>Calendario</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="user-avatar">VH</div>
          <div className="user-info">
            <strong>Usuario SIGES</strong>
            <span>Panel de gestión</span>
          </div>
          <button
            className="logout-button"
            type="button"
            onClick={async () => {
              try {
                await apiFetch('/auth/logout/', { method: 'POST' })
              } catch (error) {
                console.error('Error al cerrar sesión:', error)
              } finally {
                sessionStorage.removeItem('token')
                dispatch({ type: 'logout' })
              }
            }}
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="main-content">

        <header className="topbar">
          <div>
            <span className="breadcrumb">
              SIGES / {seccionActiva}
            </span>
            <h2>Panel de gestión</h2>
          </div>

          <div className="topbar-right">
            <span className="system-status">
              <span className="status-dot" />
              Sistema operativo
            </span>
            <div className="top-avatar">VH</div>
          </div>
        </header>

        {seccionActiva === 'inicio' && (
          <>
            <section className="welcome">
              <div>
                <span className="eyebrow">
                  SISTEMA INTEGRAL DE GESTIÓN
                </span>
                <h2>¡Bienvenida a SIGES!</h2>
                <p>
                  Administrá espacios, recursos y solicitudes de reserva
                  desde un solo lugar.
                </p>
              </div>
              <div className="welcome-icon">▦</div>
            </section>

            <section className="stats-grid">
              <article className="stat-card">
                <div className="stat-icon blue">▣</div>
                <span>Espacios registrados</span>
                <strong>{espacios.length}</strong>
                <small>Espacios del sistema</small>
              </article>

              <article className="stat-card">
                <div className="stat-icon green">✓</div>
                <span>Espacios disponibles</span>
                <strong>{espaciosDisponibles}</strong>
                <small>Actualmente disponibles</small>
              </article>

              <article className="stat-card">
                <div className="stat-icon orange">◷</div>
                <span>Actividades registradas</span>
                <strong>{actividades.filter(a => !a.cancelada).length}</strong>
                <small>Actividades no canceladas</small>
              </article>

              <article className="stat-card">
                <div className="stat-icon purple">▤</div>
                <span>Pedidos pendientes</span>
                <strong>{pendientes}</strong>
                <small>Solicitudes por asignar</small>
              </article>
            </section>

           
            <section className="panel reservation-panel">
              <div className="panel-heading">
                <div>
                  <h3>Accesos rápidos</h3>
                  <p>Continuá con las tareas principales de SIGES</p>
                </div>
              </div>

              <div className="quick-actions">
                <button type="button" onClick={() => irASeccion('reservas')}>
                  <span>＋</span>
                  <strong>Registrar un pedido</strong>
                  <small>Ingresá una nueva solicitud</small>
                </button>

                <button type="button" onClick={() => irASeccion('espacios')}>
                  <span>⌂</span>
                  <strong>Consultar espacios</strong>
                  <small>Revisá capacidad y estado</small>
                </button>

                <button type="button" onClick={() => irASeccion('recursos')}>
                  <span>▤</span>
                  <strong>Ver recursos</strong>
                  <small>Equipos asociados a los espacios</small>
                </button>
              </div>
            </section>
          </>
        )}
        {seccionActiva === 'dashboard' && (
          <section className="panel dashboard-embed-panel">
            <div className="panel-heading">
              <div>
                <h3>Panel de control</h3>
                <p>Estadísticas de reservas, actividades y equipamiento.</p>
              </div>
            </div>

            <div className="dashboard-embed">
              <iframe
                title="Dashboard de estadísticas SIGES"
                src="https://datastudio.google.com/embed/reporting/fc6b3b9d-4999-4e4a-8756-b8f6b9571cd5/page/UEJBG"
                width="100%"
                height="1100"
                style={{ border: 0, width: '100%', minHeight: '80vh' }}
                allowFullScreen
                sandbox="allow-storage-access-by-user-activation allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
              />
            </div>
          </section>
        )}
        {seccionActiva === 'reservas' && (
          <>
            <section className="panel form-panel">
              <div className="panel-heading">
                <div>
                  <h3>Nueva solicitud de espacio</h3>
                  <p>Completá los datos para registrar un pedido.</p>
                </div>
              </div>

              <form
                className="resource-form reservation-form"
                onSubmit={agregarPedido}
              >
                <div className="form-group">
                  <label htmlFor="reserva-actividad">Actividad</label>

                  <select
                    id="reserva-actividad"
                    name="actividad"
                    required
                    disabled={cargandoActividades || actividadesDisponibles.length === 0}
                  >
                  <option value="">
                    {cargandoActividades
                      ? 'Cargando actividades...'
                      : 'Seleccioná una actividad'}
                  </option>

                  {actividadesDisponibles.map(actividad => (
                    <option key={actividad.id_actividad} value={actividad.id_actividad}>
                      {actividad.nombre}
                    </option>
                  ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="reserva-fecha">Fecha de reserva</label>
                  <input
                    id="reserva-fecha"
                    name="fecha"
                    type="date"
                    min={new Date().toLocaleDateString('en-CA')}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="reserva-inicio">Hora de inicio</label>
                  <select id="reserva-inicio" name="ini" required>
                    <option value="">Seleccioná una hora</option>
                    {Array.from({ length: 13 }, (_, i) => i + 8).map(hora => (
                      <option key={hora} value={`${String(hora).padStart(2, '0')}:00`}>
                        {String(hora).padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="reserva-fin">Hora de finalización</label>
                  <select id="reserva-fin" name="fin" required>
                    <option value="">Seleccioná una hora</option>
                    {Array.from({ length: 13 }, (_, i) => i + 8).map(hora => (
                      <option key={hora} value={`${String(hora).padStart(2, '0')}:00`}>
                      {String(hora).padStart(2, '0')}:00
                    </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="reserva-detalle">Detalle</label>
                  <textarea
                    id="reserva-detalle"
                    name="detalle"
                    placeholder="Descripción adicional de la reserva"
                    rows="3"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="reserva-codigo">Código de reunión</label>
                  <input
                    id="reserva-codigo"
                    name="cod_reunion"
                    type="text"
                    placeholder="Opcional"
                  />
                </div>

                <div className="resource-form-actions">
                  <button type="submit">Registrar pedido</button>
                </div>
              </form>

              {mensaje && (
                <p className="reservation-message" role="status">
                  {mensaje}
                </p>
              )}

              {errorActividades && (
                <p className="reservation-message" role="alert">
                  Error al cargar actividades: {errorActividades}
                </p>
              )}
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Solicitudes registradas</h3>
                  <p>{reservasRegistradas.length} reservas en el sistema</p>
                </div>
              </div>

              <div className="pedidos-table-wrapper">
                <table className="pedidos-table">
                  <thead>
                    <tr>
                      <th>Actividad</th>
                      <th>Fecha</th>
                      <th>Horario</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reservasRegistradas.map(reserva => (
                      <tr key={reserva.id_reserva}>
                        <td><strong>{reserva.actividad_nombre}</strong></td>
                        <td>
                          {reserva.fecha_reserva
                            ? new Date(reserva.fecha_reserva + 'T12:00:00').toLocaleDateString('es-AR')
                            : '-'}
                        </td>
                        <td>
                        {reserva.horario_inicio} - {reserva.horario_fin}
                        </td>
                        <td>{reserva.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {seccionActiva === 'actividades' && (
            <Actividades />
        )}

        {seccionActiva === 'pedidos' && (
          <section className="panel pedidos-panel">
            <div className="panel-heading">
              <div>
                <h3>Gestión de pedidos</h3>
                <p>Evaluá solicitudes y asigná espacios disponibles.</p>
              </div>
            </div>

            <Pedidos />
          </section>
        )}

        {seccionActiva === 'espacios' && (
          <section className="panel" id="espacios">
            <div className="panel-heading">
              <div>
                <h3>Espacios registrados</h3>
                <p>Consultá capacidad, características y estado.</p>
              </div>
            </div>

            <div className="spaces-grid">
              {espacios.map(espacio => (
                <article className="space-card" key={espacio.id}>
                  <div className="space-card-top">
                    <span className="space-icon">⌂</span>
                    <span className={`status ${espacio.estado === 'Disponible' ? 'available' : espacio.estado === 'Mantenimiento' ? 'maintenance' : ''}`}>
                      {espacio.estado}
                    </span>
                  </div>

                  <h4>{espacio.nombre}</h4>
                  <p>{espacio.tipo}</p>

                  <div className="space-details">
                    <span>Capacidad: {espacio.cap} personas</span>
                    <span>Piso: {espacio.piso}</span>
                    {espacio.hasta && <span>Hasta: {espacio.hasta}</span>}
                  </div>

                  {espacio.car?.length > 0 && (
                    <div className="space-details">
                      <span>Características: {espacio.car.join(', ')}</span>
                    </div>
                  )}

                  {espacio.motivo && (
                    <p>{espacio.motivo}</p>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}

        {seccionActiva === 'recursos' && (
          <section className="panel" id="recursos">
            <div className="panel-heading">
              <div>
                <h3>Recursos y equipos</h3>
                <p>Equipamiento registrado en el sistema.</p>
              </div>
            </div>

            <div className="spaces-grid">
              {equipos.map(equipo => (
                <article className="space-card" key={equipo.id}>
                  <div className="space-card-top">
                    <span className="space-icon">📦</span>
                    <span className={`status ${equipo.estado === 'Disponible' ? 'available' : equipo.estado === 'Mantenimiento' ? 'maintenance' : ''}`}>
                      {equipo.estado}
                    </span>
                  </div>

                  <h4>{equipo.n}</h4>
                  <p>{equipo.cat}</p>

                  <div className="space-details">
                    <span>Cantidad: {equipo.cant}</span>
                    <span>Ubicación: {equipo.ubic}</span>
                    <span>{equipo.fijo ? 'Equipamiento fijo' : 'Equipamiento móvil'}</span>
                    {equipo.critico && <span>Equipo crítico</span>}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {seccionActiva === 'calendario' && (
  <section className="panel" id="calendario">
    <div className="panel-heading">
      <div>
        <h3>Calendario de actividades</h3>
        <p>Consultá y gestioná las actividades por día y espacio.</p>
      </div>
    </div>

    <Calendario />
  </section>
)}

        <footer className="footer">
          SIGES · Sistema de gestión de espacios
          <span>Versión de desarrollo</span>
        </footer>

      </main>
    </div>
  )
}

export default App
