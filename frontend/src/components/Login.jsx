
import { useState } from 'react'
import './Login.css'

function Login({ onLogin }) {
  const [usuario, setUsuario] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(event) {
    event.preventDefault()

    if (!usuario.trim() || !contrasena.trim()) {
      setError('Completá el usuario y la contraseña.')
      return
    }

    setError('')
    onLogin()
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-logo">
          <img src="/logo.jpg" alt="Logo de SIGES" />
        </div>

        <span className="login-eyebrow">
          SISTEMA INTEGRAL DE GESTIÓN
        </span>

        <h1>Bienvenida a SIGES</h1>
        <p className="login-description">
          Ingresá tus datos para acceder al sistema.
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="usuario">Usuario o correo electrónico</label>
          <input
            id="usuario"
            type="text"
            placeholder="Ingresá tu usuario"
            value={usuario}
            onChange={(event) => setUsuario(event.target.value)}
          />

          <label htmlFor="contrasena">Contraseña</label>
          <input
            id="contrasena"
            type="password"
            placeholder="Ingresá tu contraseña"
            value={contrasena}
            onChange={(event) => setContrasena(event.target.value)}
          />

          {error && <p className="login-error">{error}</p>}

          <button type="submit" className="login-button">
            Ingresar al sistema
          </button>
        </form>

        <p className="login-footer">
          SIGES · Gestión de espacios
        </p>
      </section>
    </main>
  )
}

export default Login
