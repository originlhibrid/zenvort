const BASE_URL = 'https://zenvort.devbrid.in/api'

export { BASE_URL }

async function request(path, options = {}) {
  const token = localStorage.getItem('zenvort_api_key')
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
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
      fetch(`${BASE_URL}/jobs`, {
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
