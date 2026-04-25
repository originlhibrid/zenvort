const BASE_URL = 'http://localhost:3000';

function authHeader() {
  return { 'Authorization': 'Bearer ' + localStorage.getItem('zenvort_api_key') };
}

async function request(path, options = {}) {
  const res = await fetch(BASE_URL + path, {
    ...options,
    headers: { ...authHeader(), ...options.headers }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'Request failed');
  return data;
}

export const api = {
  login: (email, password) => request('/auth/login', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({email, password}) }),
  signup: (email, password) => request('/auth/signup', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({email, password}) }),
  getMe: () => request('/user/me'),
  listJobs: (page=1) => request('/jobs?page=' + page + '&limit=20'),
  getJob: (id) => request('/jobs/' + id),
  createJob: (file, outputFormat) => {
    const form = new FormData();
    form.append('file', file);
    form.append('outputFormat', outputFormat);
    return fetch(BASE_URL + '/jobs', { method: 'POST', headers: authHeader(), body: form }).then(r => r.json());
  },
  getUsage: () => request('/billing/usage'),
  getPlans: () => request('/billing/plans'),
  getTransactions: () => request('/billing/transactions'),
  updateWebhook: (webhookUrl) => request('/user/webhook', { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify({webhookUrl}) }),
  adminStats: () => request('/admin/stats'),
  adminUsers: (page=1) => request('/admin/users?page=' + page),
  adminAdjustCredits: (id, amount) => request('/admin/users/' + id + '/credits', { method: 'PATCH', headers: {'Content-Type':'application/json'}, body: JSON.stringify({amount}) })
};