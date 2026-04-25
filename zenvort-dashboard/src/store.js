export const Store = {
  getApiKey: () => localStorage.getItem('zenvort_api_key'),
  getUser: () => { try { return JSON.parse(localStorage.getItem('zenvort_user')); } catch { return null; } },
  setAuth: (apiKey, user) => { localStorage.setItem('zenvort_api_key', apiKey); localStorage.setItem('zenvort_user', JSON.stringify(user)); },
  clearAuth: () => { localStorage.removeItem('zenvort_api_key'); localStorage.removeItem('zenvort_user'); },
  isAuthenticated: () => !!localStorage.getItem('zenvort_api_key')
};