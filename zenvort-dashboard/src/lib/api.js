const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3001/api'

async function request(path, options = {}) {
  const token = localStorage.getItem('zenvort_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.message || 'Request failed')
  }
  return res.json()
}

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  register: (email, password, name) => request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, name }) }),
  me: () => request('/auth/me'),
  convert: (formData) =>
    fetch(`${API_BASE}/convert`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('zenvort_token')}` },
      body: formData,
    }),
  jobs: () => request('/jobs'),
  download: (jobId) => `${API_BASE}/download/${jobId}`,
}