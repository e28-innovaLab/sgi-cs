const API_URL = '/api'

export async function apiFetch(endpoint, options = {}) {
  const token = sessionStorage.getItem('token')

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers.Authorization = `Token ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (response.status === 204) {
    return null
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const errores = data && typeof data === 'object'
      ? Object.values(data).flat()
      : []

    const mensaje =
      data?.detail ||
      errores.find(error => typeof error === 'string') ||
      'Ocurrió un error al comunicarse con el servidor.'

    throw new Error(mensaje)
  }

  return data
}
