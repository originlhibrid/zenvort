const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000'

async function request(path, options = {}) {
  const token = localStorage.getItem('zenvort_api_key')
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.error || err.message || 'Request failed')
  }
  return res.json()
}

export const api = {
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),

  register: (email, password) =>
    request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) }),

  me: () => request('/user/me'),

  jobs: {
    list: () => request('/jobs'),
    get: (id) => request(`/jobs/${id}`),
    submit: (formData) =>
      fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('zenvort_api_key')}` },
        body: formData,
      }),
  },

  billing: {
    plans: () => request('/billing/plans'),
    usage: () => request('/billing/usage'),
    transactions: () => request('/billing/transactions'),
  },
}