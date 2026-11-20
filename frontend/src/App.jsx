
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import './App.css'
import Login from './components/Login'
import Pedidos from './pages/Pedidos.jsx';
import { useStore } from './store.jsx'
import { DIAS, AREAS } from './data/mocks.js'

function App() {
  const { state, dispatch } = useStore()
  const navigate = useNavigate()
  const location = useLocation()

  const [logueado, setLogueado] = useState(false)
  const [mensaje, setMensaje] = useState('')

  const espacios = state.espacios
  const equipos = state.equipos
  const actividades = state.actividades
  const pedidos = state.pedidos

  const seccionActiva =
    location.pathname === '/'
      ? 'inicio'
      : location.pathname.replace('/', '')

  function irASeccion(seccion) {
    navigate(seccion === 'inicio' ? '/' : `/${seccion}`)
  }

  function agregarPedido(event) {
    event.preventDefault()

    const formulario = new FormData(event.currentTarget)

    const titulo = formulario.get('titulo').trim()
    const dia = Number(formulario.get('dia'))
    const ini = Number(formulario.get('ini'))
    const fin = Number(formulario.get('fin'))
    const cupo = Number(formulario.get('cupo'))
    const sol = formulario.get('sol')
    const resp = formulario.get('resp').trim()
    const equipo = formulario.get('equipo')
    const cantidadEquipo = Number(formulario.get('cantidadEquipo'))

    if (fin <= ini) {
      setMensaje('La hora de finalización debe ser posterior a la hora de inicio.')
      return
    }

    if (ini < 8 || fin > 20) {
      setMensaje('El horario debe estar comprendido entre las 8 y las 20 hs.')
      return
    }

    const req = equipo
      ? [{ n: equipo, cant: cantidadEquipo }]
      : []

    const nuevoPedido = {
      id: 'p' + Date.now(),
      canal: 'Formulario',
      sol,
      titulo,
      tipo: 'Solicitud',
      dia,
      ini,
      fin,
      cupo,
      resp,
      req,
      estado: 'Por asignar',
    }

    dispatch({ type: 'pedidoNuevo', pedido: nuevoPedido })

    event.currentTarget.reset()
    setMensaje('El pedido se registró correctamente.')
  }

  const pendientes = pedidos.filter(
    pedido => pedido.estado === 'Por asignar'
  ).length

  const espaciosDisponibles = espacios.filter(
    espacio => espacio.estado === 'Disponible'
  ).length

  if (!logueado) {
    return <Login onLogin={() => setLogueado(true)} />
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
            onClick={() => setLogueado(false)}
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

            <section className="panel dashboard-panel">
              <div className="panel-heading">
                <div>
                  <h3>Espacios</h3>
                  <p>Estado de los espacios registrados</p>
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
                    </div>
                  </article>
                ))}
              </div>
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
                  <label htmlFor="pedido-titulo">Actividad o motivo</label>
                  <input
                    id="pedido-titulo"
                    name="titulo"
                    type="text"
                    placeholder="Ej. Capacitación de equipo"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-area">Área solicitante</label>
                  <select id="pedido-area" name="sol" required>
                    {AREAS.map(area => (
                      <option key={area} value={area}>{area}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-responsable">Responsable</label>
                  <input
                    id="pedido-responsable"
                    name="resp"
                    type="text"
                    placeholder="Nombre del responsable"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-dia">Día</label>
                  <select id="pedido-dia" name="dia" required>
                    {DIAS.map((dia, index) => (
                      <option key={dia} value={index}>{dia}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-inicio">Hora de inicio</label>
                  <select id="pedido-inicio" name="ini" required>
                    {Array.from({ length: 13 }, (_, i) => i + 8).map(hora => (
                      <option key={hora} value={hora}>
                        {String(hora).padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-fin">Hora de finalización</label>
                  <select id="pedido-fin" name="fin" required>
                    {Array.from({ length: 13 }, (_, i) => i + 8).map(hora => (
                      <option key={hora} value={hora}>
                        {String(hora).padStart(2, '0')}:00
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-cupo">Cantidad de personas</label>
                  <input
                    id="pedido-cupo"
                    name="cupo"
                    type="number"
                    min="1"
                    placeholder="Ej. 20"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-equipo">Equipamiento solicitado</label>
                  <select id="pedido-equipo" name="equipo">
                    <option value="">Sin equipamiento adicional</option>
                    {[...new Set(equipos.map(equipo => equipo.n))].map(nombre => (
                      <option key={nombre} value={nombre}>{nombre}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="pedido-cantidad-equipo">Cantidad de equipos</label>
                  <input
                    id="pedido-cantidad-equipo"
                    name="cantidadEquipo"
                    type="number"
                    min="1"
                    defaultValue="1"
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
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Solicitudes registradas</h3>
                  <p>{pedidos.length} pedidos en el sistema</p>
                </div>
              </div>

              <div className="pedidos-table-wrapper">
                <table className="pedidos-table">
                  <thead>
                    <tr>
                      <th>Actividad</th>
                      <th>Área</th>
                      <th>Día</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pedidos.map(pedido => (
                      <tr key={pedido.id}>
                        <td><strong>{pedido.titulo}</strong></td>
                        <td>{pedido.sol}</td>
                        <td>{DIAS[pedido.dia]}</td>
                        <td>{pedido.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {seccionActiva === 'pedidos' && (
          <section className="panel pedidos-panel">
            <div className="panel-heading">
              <div>
                <h3>Gestión de pedidos</h3>
                <p>Evaluá solicitudes y asigná espacios disponibles.</p>
              </div>
              <span className="pedidos-total">{pedidos.length} pedidos</span>
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
          <section className="panel" id="espacios">
            <div className="panel-heading">
              <div>
                <h3>Calendario de actividades</h3>
                <p>Actividades registradas por día y espacio.</p>
              </div>
            </div>

            {DIAS.map((dia, index) => {
              const actividadesDia = actividades.filter(
                actividad => actividad.dia === index && !actividad.cancelada
              )

              return (
                <div className="panel" key={dia}>
                  <h4>{dia}</h4>

                  {actividadesDia.length === 0 ? (
                    <p>No hay actividades registradas.</p>
                  ) : (
                    <div className="spaces-grid">
                      {actividadesDia.map(actividad => {
                        const espacio = espacios.find(
                          item => item.id === actividad.sp
                        )

                        return (
                          <article className="space-card" key={actividad.id}>
                            <h4>{actividad.titulo}</h4>
                            <p>{actividad.tipo}</p>
                            <div className="space-details">
                              <span>
                                Horario: {actividad.ini}:00 a {actividad.fin}:00 hs
                              </span>
                              <span>Espacio: {espacio?.nombre || 'Sin asignar'}</span>
                              <span>Participantes: {actividad.insc}</span>
                              <span>Responsable: {actividad.resp}</span>
                            </div>
                          </article>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
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
