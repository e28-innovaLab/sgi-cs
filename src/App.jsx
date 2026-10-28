import { useState } from 'react'
import './App.css'
import Login from './components/Login'

const espacios = [
  { nombre: 'Aula 01', tipo: 'Aula', capacidad: 30, estado: 'Disponible' },
  { nombre: 'Laboratorio 02', tipo: 'Laboratorio', capacidad: 20, estado: 'Ocupado' },
  { nombre: 'Sala de reuniones', tipo: 'Sala', capacidad: 12, estado: 'Disponible' },
  { nombre: 'Auditorio principal', tipo: 'Auditorio', capacidad: 100, estado: 'Mantenimiento' },
]

function App() {
  const [logueado, setLogueado] = useState(false)
  const [seccionActiva, setSeccionActiva] = useState('inicio')

  const [recursos, setRecursos] = useState(() => {
    const guardados = localStorage.getItem('siges-recursos')

    if (guardados) return JSON.parse(guardados)

    return [
      {
        id: 1,
        nombre: 'Proyector',
        categoria: 'Equipo audiovisual',
        cantidad: 4,
        espacio: 'Auditorio principal',
        estado: 'Disponible',
      },
      {
        id: 2,
        nombre: 'Computadoras',
        categoria: 'Equipos informáticos',
        cantidad: 20,
        espacio: 'Laboratorio 02',
        estado: 'Disponible',
      },
      {
        id: 3,
        nombre: 'Micrófonos',
        categoria: 'Equipo de audio',
        cantidad: 2,
        espacio: 'Auditorio principal',
        estado: 'Mantenimiento',
      },
    ]
  })

  const [recursoEditando, setRecursoEditando] = useState(null)

  const [reservas, setReservas] = useState(() => {
    const guardadas = localStorage.getItem('siges-reservas')
    return guardadas ? JSON.parse(guardadas) : []
  })

  const [espacioReserva, setEspacioReserva] = useState(
    espacios.find((espacio) => espacio.estado !== 'Mantenimiento')?.nombre ||
    espacios[0].nombre
  )

  const [mensajeReserva, setMensajeReserva] = useState('')
  const [tipoMensajeReserva, setTipoMensajeReserva] = useState('')

  function guardarRecursos(nuevosRecursos) {
    setRecursos(nuevosRecursos)
    localStorage.setItem('siges-recursos', JSON.stringify(nuevosRecursos))
  }

  function guardarReservas(nuevasReservas) {
    setReservas(nuevasReservas)
    localStorage.setItem('siges-reservas', JSON.stringify(nuevasReservas))
  }

  function agregarReserva(event) {
    event.preventDefault()

    const formulario = new FormData(event.currentTarget)

    const actividad = formulario.get('actividad').trim()
    const fecha = formulario.get('fecha')
    const horaInicio = formulario.get('horaInicio')
    const horaFin = formulario.get('horaFin')
    const espacio = formulario.get('espacio')
    const participantes = Number(formulario.get('participantes'))
    const recursosSeleccionados = formulario.getAll('recursos').map(Number)

    if (horaFin <= horaInicio) {
      setTipoMensajeReserva('error')
      setMensajeReserva(
        'La hora de finalización debe ser posterior a la hora de inicio.'
      )
      return
    }

    const espacioElegido = espacios.find((item) => item.nombre === espacio)

    if (!espacioElegido) {
      setTipoMensajeReserva('error')
      setMensajeReserva('Seleccioná un espacio válido.')
      return
    }

    if (espacioElegido.estado === 'Mantenimiento') {
      setTipoMensajeReserva('error')
      setMensajeReserva(
        'Este espacio está en mantenimiento. Elegí otro espacio.'
      )
      return
    }

    if (participantes > espacioElegido.capacidad) {
      setTipoMensajeReserva('error')
      setMensajeReserva(
        `La capacidad máxima de ${espacioElegido.nombre} es de ${espacioElegido.capacidad} personas.`
      )
      return
    }

    const nuevaReserva = {
      id: Date.now(),
      actividad,
      fecha,
      horaInicio,
      horaFin,
      espacio,
      participantes,
      recursos: recursosSeleccionados,
      estado: 'Pendiente',
    }

    guardarReservas([...reservas, nuevaReserva])

    event.currentTarget.reset()

    setEspacioReserva(
      espacios.find((item) => item.estado !== 'Mantenimiento')?.nombre ||
        espacios[0].nombre
    )

    setTipoMensajeReserva('exito')
    setMensajeReserva('La solicitud de reserva se registró correctamente.')
  }

  function eliminarReserva(id) {
    guardarReservas(reservas.filter((reserva) => reserva.id !== id))
    setTipoMensajeReserva('exito')
    setMensajeReserva('La solicitud se eliminó correctamente.')
  }

  function agregarRecurso(event) {
    event.preventDefault()

    const formulario = new FormData(event.currentTarget)

    const datosRecurso = {
      nombre: formulario.get('nombre').trim(),
      categoria: formulario.get('categoria'),
      cantidad: Number(formulario.get('cantidad')),
      espacio: formulario.get('espacio'),
      estado: formulario.get('estado'),
    }

    if (recursoEditando) {
      const recursosActualizados = recursos.map((recurso) =>
        recurso.id === recursoEditando.id
          ? { ...recurso, ...datosRecurso }
          : recurso
      )

      guardarRecursos(recursosActualizados)
      setRecursoEditando(null)
    } else {
      const nuevoRecurso = {
        id: Date.now(),
        ...datosRecurso,
      }

      guardarRecursos([...recursos, nuevoRecurso])
    }

    event.currentTarget.reset()
  }

  function eliminarRecurso(id) {
    const nuevosRecursos = recursos.filter((recurso) => recurso.id !== id)

    guardarRecursos(nuevosRecursos)

    if (recursoEditando?.id === id) {
      setRecursoEditando(null)
    }
  }

  function editarRecurso(recurso) {
    setRecursoEditando(recurso)
  }

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
            href="#inicio"
            onClick={() => setSeccionActiva('inicio')}
          >
            ▦ <span>Inicio</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'reservas' ? 'active' : ''}`}
            href="#reservas"
            onClick={() => setSeccionActiva('reservas')}
          >
            ▣ <span>Reservas</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'espacios' ? 'active' : ''}`}
            href="#espacios"
            onClick={() => setSeccionActiva('espacios')}
          >
            ⌂ <span>Espacios</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'recursos' ? 'active' : ''}`}
            href="#recursos"
            onClick={() => setSeccionActiva('recursos')}
          >
            ▤ <span>Recursos y equipos</span>
          </a>

          <a
            className={`menu-item ${seccionActiva === 'listado-reservas' ? 'active' : ''}`}
            href="#listado-reservas"
            onClick={() => setSeccionActiva('listado-reservas')}
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
            onClick={() => setLogueado(false)}
            type="button"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="main-content" id="inicio">
        <header className="topbar">
          <div>
            <span className="breadcrumb">SIGES / Inicio</span>
            <h2>Panel de gestión</h2>
          </div>

          <div className="topbar-right">
            <span className="system-status">
              <span className="status-dot" /> Sistema operativo
            </span>
            <div className="top-avatar">VH</div>
          </div>
        </header>

        <section className="welcome">
          <div>
            <span className="eyebrow">SISTEMA INTEGRAL DE GESTIÓN</span>
            <h2>¡Bienvenida a SIGES!</h2>
            <p>
              Administrá espacios, recursos y solicitudes de reserva desde un
              solo lugar.
            </p>
          </div>

          <div className="welcome-icon">▦</div>
        </section>

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-icon blue">▣</div>
            <span>Espacios registrados</span>
            <strong>{espacios.length}</strong>
            <small>Espacios en el sistema</small>
          </article>

          <article className="stat-card">
            <div className="stat-icon green">✓</div>
            <span>Disponibles ahora</span>
            <strong>
              {espacios.filter((espacio) => espacio.estado === 'Disponible').length}
            </strong>
            <small>Con estado disponible</small>
          </article>

          <article className="stat-card">
            <div className="stat-icon orange">◷</div>
            <span>Solicitudes pendientes</span>
            <strong>
              {reservas.filter((reserva) => reserva.estado === 'Pendiente').length}
            </strong>
            <small>Requieren seguimiento</small>
          </article>

          <article className="stat-card">
            <div className="stat-icon purple">▤</div>
            <span>Recursos disponibles</span>
            <strong>
              {recursos
                .filter((recurso) => recurso.estado === 'Disponible')
                .reduce((total, recurso) => total + recurso.cantidad, 0)}
            </strong>
            <small>Unidades disponibles registradas</small>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel spaces-panel" id="espacios">
            <div className="panel-heading">
              <div>
                <h3>Espacios</h3>
                <p>Estado actual de los espacios registrados</p>
              </div>

              <button
                className="text-button"
                type="button"
                onClick={() =>
                  document
                    .getElementById('form-reserva')
                    ?.scrollIntoView({ behavior: 'smooth' })
                }
              >
                Nueva reserva +
              </button>
            </div>

            <div className="spaces-list">
              {espacios.map((espacio) => (
                <div className="space-row" key={espacio.nombre}>
                  <div className="space-icon">⌂</div>

                  <div className="space-details">
                    <strong>{espacio.nombre}</strong>
                    <span>
                      {espacio.tipo} · Capacidad: {espacio.capacidad} personas
                    </span>
                  </div>

                  <span
                    className={`badge ${espacio.estado
                      .toLowerCase()
                      .replace('ó', 'o')}`}
                  >
                    {espacio.estado}
                  </span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel activity-panel">
            <div className="panel-heading">
              <div>
                <h3>Actividad reciente</h3>
                <p>Resumen de movimientos</p>
              </div>

              <span className="activity-symbol">◷</span>
            </div>

            {reservas.length === 0 ? (
              <div className="empty-activity">
                <div className="empty-icon">▤</div>
                <strong>Todo listo para empezar</strong>
                <p>
                  Cuando registres reservas, vas a poder consultarlas desde
                  esta sección.
                </p>
              </div>
            ) : (
              <div className="spaces-list">
                {reservas.slice(-3).reverse().map((reserva) => (
                  <div className="space-row" key={reserva.id}>
                    <div className="space-icon">📅</div>
                    <div className="space-details">
                      <strong>{reserva.actividad}</strong>
                      <span>
                        {reserva.fecha} · {reserva.espacio}
                      </span>
                    </div>
                    <span className="badge">{reserva.estado}</span>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>

        <section className="panel reservation-panel" id="reservas">
          <div className="panel-heading">
            <div>
              <h3>Accesos rápidos</h3>
              <p>Continuá con las tareas principales de SIGES</p>
            </div>
          </div>

          <div className="quick-actions">
            <button
              type="button"
              onClick={() =>
                document
                  .getElementById('form-reserva')
                  ?.scrollIntoView({ behavior: 'smooth' })
              }
            >
              <span>＋</span>
              <strong>Solicitar una reserva</strong>
              <small>Elegí fecha, horario y espacio</small>
            </button>

            <button
              type="button"
              onClick={() =>
                document
                  .getElementById('espacios')
                  ?.scrollIntoView({ behavior: 'smooth' })
              }
            >
              <span>⌂</span>
              <strong>Consultar espacios</strong>
              <small>Revisá capacidad y estado</small>
            </button>

            <button
              type="button"
              onClick={() =>
                document
                  .getElementById('recursos')
                  ?.scrollIntoView({ behavior: 'smooth' })
              }
            >
              <span>▤</span>
              <strong>Ver recursos</strong>
              <small>Equipos asociados a los espacios</small>
            </button>
          </div>
        </section>

        <section className="panel form-panel" id="form-reserva">
          <div className="panel-heading">
            <div>
              <h3>Nueva solicitud de reserva</h3>
              <p>
                Completá los datos de la actividad y elegí el espacio que
                necesitás.
              </p>
            </div>
          </div>

          <form
            className="resource-form reservation-form"
            onSubmit={agregarReserva}
          >
            <div className="form-group">
              <label htmlFor="actividad-reserva">Actividad o motivo</label>
              <input
                id="actividad-reserva"
                type="text"
                name="actividad"
                placeholder="Ej. Capacitación de equipo"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="fecha-reserva">Fecha</label>
              <input
                id="fecha-reserva"
                type="date"
                name="fecha"
                min={new Date().toLocaleDateString('en-CA')}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="hora-inicio-reserva">Hora de inicio</label>
              <input
                id="hora-inicio-reserva"
                type="time"
                name="horaInicio"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="hora-fin-reserva">Hora de finalización</label>
              <input
                id="hora-fin-reserva"
                type="time"
                name="horaFin"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="espacio-reserva">Espacio</label>
              <select
                id="espacio-reserva"
                name="espacio"
                value={espacioReserva}
                onChange={(event) => setEspacioReserva(event.target.value)}
                required
              >
                {espacios.map((espacio) => (
                  <option
                    key={espacio.nombre}
                    value={espacio.nombre}
                    disabled={espacio.estado === 'Mantenimiento'}
                  >
                    {espacio.nombre} — capacidad {espacio.capacidad}
                    {espacio.estado === 'Mantenimiento'
                      ? ' (En mantenimiento)'
                      : ''}
                  </option>
                ))}
              </select>
              <small>
                Los espacios en mantenimiento no se pueden seleccionar.
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="participantes-reserva">
                Cantidad de participantes
              </label>
              <input
                id="participantes-reserva"
                type="number"
                name="participantes"
                min="1"
                max={
                  espacios.find(
                    (espacio) => espacio.nombre === espacioReserva
                  )?.capacidad
                }
                placeholder="Ej. 15"
                required
              />
              <small>
                Capacidad máxima:{' '}
                {
                  espacios.find(
                    (espacio) => espacio.nombre === espacioReserva
                  )?.capacidad
                }{' '}
                personas.
              </small>
            </div>

            <div className="form-group">
              <label>Recursos y equipos disponibles</label>

              {recursos.some(
                (recurso) =>
                  recurso.espacio === espacioReserva &&
                  recurso.estado === 'Disponible'
              ) ? (
                <div className="reservation-resources">
                  {recursos
                    .filter(
                      (recurso) =>
                        recurso.espacio === espacioReserva &&
                        recurso.estado === 'Disponible'
                    )
                    .map((recurso) => (
                      <label
                        className="reservation-resource-option"
                        key={recurso.id}
                      >
                        <input
                          type="checkbox"
                          name="recursos"
                          value={recurso.id}
                        />
                        <span>
                          <strong>{recurso.nombre}</strong>
                          <small>
                            Cantidad disponible: {recurso.cantidad}
                          </small>
                        </span>
                      </label>
                    ))}
                </div>
              ) : (
                <p className="form-hint">
                  No hay recursos disponibles asociados a este espacio.
                </p>
              )}
            </div>

            <div className="resource-form-actions">
              <button type="submit">Enviar solicitud</button>
            </div>
          </form>

          {mensajeReserva && (
            <p
              className={`reservation-message ${tipoMensajeReserva}`}
              role="status"
            >
              {mensajeReserva}
            </p>
          )}
        </section>

        <section className="panel" id="listado-reservas">
          <div className="panel-heading">
            <div>
              <h3>Reservas registradas</h3>
              <p>
                Solicitudes guardadas en este navegador: {reservas.length}
              </p>
            </div>
          </div>

          {reservas.length === 0 ? (
            <div className="form-placeholder">
              <span>📅</span>
              <div>
                <strong>Todavía no hay reservas</strong>
                <p>
                  Cuando envíes una solicitud, va a aparecer en este listado.
                </p>
              </div>
            </div>
          ) : (
            <div className="spaces-grid">
              {reservas.map((reserva) => {
                const nombresRecursos = reserva.recursos
                  .map(
                    (idRecurso) =>
                      recursos.find((recurso) => recurso.id === idRecurso)
                        ?.nombre
                  )
                  .filter(Boolean)

                return (
                  <article className="space-card" key={reserva.id}>
                    <div className="space-card-top">
                      <span className="space-icon">📅</span>
                      <span className="status">{reserva.estado}</span>
                    </div>

                    <h4>{reserva.actividad}</h4>
                    <p>{reserva.espacio}</p>

                    <div className="space-details">
                      <span>Fecha: {reserva.fecha}</span>
                      <span>
                        Horario: {reserva.horaInicio} a {reserva.horaFin}
                      </span>
                      <span>Participantes: {reserva.participantes}</span>
                      <span>
                        Recursos:{' '}
                        {nombresRecursos.length
                          ? nombresRecursos.join(', ')
                          : 'Ninguno'}
                      </span>
                    </div>

                    <div className="resource-actions">
                      <button
                        type="button"
                        className="delete-button"
                        onClick={() => eliminarReserva(reserva.id)}
                      >
                        Eliminar solicitud
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </section>

        <section className="panel" id="recursos">
          <div className="panel-heading">
            <div>
              <h3>Recursos y equipos</h3>
              <p>Consultá los equipos disponibles para cada espacio</p>
            </div>
          </div>

          <form
            key={recursoEditando?.id ?? 'nuevo'}
            id="form-recursos"
            className="form-panel resource-form"
            onSubmit={agregarRecurso}
          >
            <h4>
              {recursoEditando ? 'Editar recurso' : 'Agregar recurso'}
            </h4>

            <div className="form-group">
              <label htmlFor="nombre-recurso">Nombre del recurso</label>
              <input
                id="nombre-recurso"
                type="text"
                name="nombre"
                placeholder="Ej. Proyector"
                defaultValue={recursoEditando?.nombre || ''}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="categoria-recurso">Categoría</label>
              <select
                id="categoria-recurso"
                name="categoria"
                defaultValue={
                  recursoEditando?.categoria || 'Equipo audiovisual'
                }
                required
              >
                <option value="Equipo audiovisual">
                  Equipo audiovisual
                </option>
                <option value="Equipos informáticos">
                  Equipos informáticos
                </option>
                <option value="Equipo de audio">Equipo de audio</option>
                <option value="Otro">Otro</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="cantidad-recurso">Cantidad</label>
              <input
                id="cantidad-recurso"
                type="number"
                name="cantidad"
                min="1"
                defaultValue={recursoEditando?.cantidad ?? 1}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="espacio-recurso">Espacio asociado</label>
              <select
                id="espacio-recurso"
                name="espacio"
                defaultValue={recursoEditando?.espacio || espacios[0].nombre}
                required
              >
                {espacios.map((espacio) => (
                  <option key={espacio.nombre} value={espacio.nombre}>
                    {espacio.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="estado-recurso">Estado</label>
              <select
                id="estado-recurso"
                name="estado"
                defaultValue={recursoEditando?.estado || 'Disponible'}
                required
              >
                <option value="Disponible">Disponible</option>
                <option value="En uso">En uso</option>
                <option value="Mantenimiento">Mantenimiento</option>
              </select>
            </div>

            <div className="resource-form-actions">
              <button type="submit">
                {recursoEditando ? 'Guardar cambios' : 'Agregar recurso'}
              </button>

              {recursoEditando && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setRecursoEditando(null)}
                >
                  Cancelar edición
                </button>
              )}
            </div>
          </form>

          <div className="spaces-grid">
            {recursos.map((recurso) => (
              <article className="space-card" key={recurso.id}>
                <div className="space-card-top">
                  <span className="space-icon">📦</span>

                  <span
                    className={`status ${
                      recurso.estado === 'Disponible'
                        ? 'available'
                        : recurso.estado === 'Mantenimiento'
                          ? 'maintenance'
                          : ''
                    }`}
                  >
                    {recurso.estado}
                  </span>
                </div>

                <h4>{recurso.nombre}</h4>
                <p>{recurso.categoria}</p>

                <div className="space-details">
                  <span>Cantidad: {recurso.cantidad}</span>
                  <span>{recurso.espacio}</span>
                </div>

                <div className="resource-actions">
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => editarRecurso(recurso)}
                  >
                    Editar
                  </button>

                  <button
                    type="button"
                    className="delete-button"
                    onClick={() => eliminarRecurso(recurso.id)}
                  >
                    Eliminar
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <footer className="footer">
          SIGES · Sistema de gestión de espacios
          <span>Versión de desarrollo</span>
        </footer>
      </main>
    </div>
  )
}

export default App