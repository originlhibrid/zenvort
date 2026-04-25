// ============================================================
//  ZENVORT DASHBOARD — ALL-IN-ONE
// ============================================================

// Destructure Preact
var h = preact.h;
var render = preact.render;
var Component = preact.Component;
var useState = preactHooks.useState;
var useEffect = preactHooks.useEffect;
var useRef = preactHooks.useRef;

// ============================================================
//  CONFIG & STORAGE
// ============================================================

var CONFIG = { BASE_URL: 'http://localhost:3000' };

var Store = {
  getApiKey: function() { return localStorage.getItem('zenvort_api_key'); },
  getUser: function() { var u = localStorage.getItem('zenvort_user'); return u ? JSON.parse(u) : null; },
  getAuth: function() { return { apiKey: this.getApiKey(), user: this.getUser() }; },
  setAuth: function(apiKey, user) {
    localStorage.setItem('zenvort_api_key', apiKey);
    localStorage.setItem('zenvort_user', JSON.stringify(user));
  },
  clearAuth: function() {
    localStorage.removeItem('zenvort_api_key');
    localStorage.removeItem('zenvort_user');
  },
  isAuthenticated: function() { return !!this.getApiKey(); },
};

// ============================================================
//  API LAYER
// ============================================================

function authHeaders(contentType) {
  var h = {};
  if (contentType) h['Content-Type'] = contentType;
  var k = Store.getApiKey();
  if (k) h['Authorization'] = 'Bearer ' + k;
  return h;
}

function apiReq(endpoint, options) {
  options = options || {};
  var url = CONFIG.BASE_URL + endpoint;
  return fetch(url, {
    method: options.method || 'GET',
    headers: Object.assign({}, authHeaders(options.contentType), options.headers || {}),
    body: options.body,
  }).then(function(res) {
    return res.text().then(function(text) {
      var data = text ? JSON.parse(text) : {};
      if (!res.ok) throw new Error(data.error || data.message || 'Request failed');
      return data;
    });
  }).catch(function(err) {
    if (err.name === 'TypeError') throw new Error('Network error: cannot reach server');
    throw err;
  });
}

var API = {
  // Auth
  signup: function(email, password) {
    return apiReq('/auth/signup', { method: 'POST', body: JSON.stringify({email: email, password: password}), contentType: 'application/json' });
  },
  login: function(email, password) {
    return apiReq('/auth/login', { method: 'POST', body: JSON.stringify({email: email, password: password}), contentType: 'application/json' });
  },

  // User
  getMe: function() { return apiReq('/user/me'); },

  // Jobs
  getJobs: function(page, limit) {
    page = page || 1; limit = limit || 20;
    return apiReq('/jobs?page=' + page + '&limit=' + limit);
  },
  getJob: function(id) { return apiReq('/jobs/' + id); },
  createJob: function(file, outputFormat) {
    var formData = new FormData();
    formData.append('file', file);
    formData.append('outputFormat', outputFormat);
    return fetch(CONFIG.BASE_URL + '/jobs', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + Store.getApiKey() },
      body: formData,
    }).then(function(res) {
      return res.json().then(function(data) {
        if (!res.ok) throw new Error(data.error || 'Failed to create job');
        return data;
      });
    });
  },

  // Billing
  getPlans: function() { return apiReq('/billing/plans'); },
  getUsage: function() { return apiReq('/billing/usage'); },
  getTransactions: function() { return apiReq('/billing/transactions'); },

  // Webhook
  updateWebhook: function(url) {
    return apiReq('/user/webhook', { method: 'PATCH', body: JSON.stringify({webhookUrl: url}), contentType: 'application/json' });
  },

  // Admin
  getAdminStats: function() { return apiReq('/admin/stats'); },
  getAdminUsers: function(page) { return apiReq('/admin/users?page=' + (page || 1)); },
  adjustCredits: function(userId, amount) {
    return apiReq('/admin/users/' + userId + '/credits', { method: 'PATCH', body: JSON.stringify({amount: amount}), contentType: 'application/json' });
  },
};

// ============================================================
//  TOAST
// ============================================================

var Toast = {
  toasts: [],
  show: function(message, type) {
    type = type || 'success';
    var id = Date.now() + Math.random();
    this.toasts.push({ id: id, message: message, type: type });
    this.render();
    var self = this;
    setTimeout(function() { self.remove(id); }, 4000);
  },
  remove: function(id) {
    this.toasts = this.toasts.filter(function(t) { return t.id !== id; });
    this.render();
  },
  render: function() {
    var el = document.getElementById('toast-container');
    if (!el) return;
    var colors = { success: 'bg-green-500', error: 'bg-red-500', info: 'bg-blue-500' };
    var icons = { success: '✓', error: '✕', info: 'ℹ' };
    var self = this;
    el.innerHTML = this.toasts.map(function(t) {
      return '<div class="flex items-center gap-3 px-5 py-4 rounded-xl shadow-lg ' + colors[t.type] + ' text-white animate-slide-in mb-3">' +
        '<span class="font-bold">' + icons[t.type] + '</span>' +
        '<span class="flex-1">' + t.message + '</span>' +
        '<button onclick="Toast.remove(' + t.id + ')" class="text-white/80 hover:text-white text-xl leading-none ml-2">×</button>' +
      '</div>';
    }).join('');
  },
};

window.showToast = function(msg, type) { Toast.show(msg, type); };
window.Toast = Toast;

// ============================================================
//  ROUTER
// ============================================================

var Router = {
  routes: {},
  subscribe: null,

  register: function(path, component) { this.routes[path] = component; },

  onRoute: function(cb) { this.subscribe = cb; },

  navigate: function(path) { window.location.hash = path; },

  getPath: function() { return window.location.hash.slice(1) || '/landing'; },

  match: function(path) {
    if (this.routes[path]) return this.routes[path];
    if (path === '/' || path === '') return this.routes['/landing'];
    return null;
  },

  handle: function() {
    var path = this.getPath();
    var component = this.match(path);
    var user = Store.getUser();
    var isAuth = Store.isAuthenticated();
    var isAdmin = user && user.role === 'admin';

    var protectedRoutes = ['/dashboard', '/keys', '/billing', '/admin'];
    var isProtected = protectedRoutes.indexOf(path) !== -1;
    var isPublic = ['/landing', '/login', '/signup'].indexOf(path) !== -1;

    var target = null;

    if (isProtected && !isAuth) {
      target = '/login';
      sessionStorage.setItem('returnTo', path);
      showToast('Please sign in to continue', 'info');
    } else if (path === '/admin' && !isAdmin) {
      target = '/dashboard';
      showToast('Admin access required', 'error');
    } else if (isPublic && isAuth) {
      target = '/dashboard';
    }

    if (target) {
      this.navigate(target);
      return;
    }

    if (component && this.subscribe) {
      this.subscribe(component, path);
    }
  },

  init: function() {
    var self = this;
    window.addEventListener('hashchange', function() { self.handle(); });
    window.addEventListener('load', function() { self.handle(); });
  },
};

// ============================================================
//  COMPONENTS
// ============================================================

// StatCard
function StatCard(props) {
  return html'<div class="bg-white rounded-xl shadow-sm p-6"><div class="flex items-center justify-between"><div><p class="text-sm text-gray-500 mb-1">${props.title}</p><p class="text-2xl font-bold text-gray-900">${props.value}</p></div><div class="text-3xl">${props.icon}</div></div></div>';
}

// JobTable
function JobTable(props) {
  var statusColors = { PENDING: 'bg-yellow-100 text-yellow-800', PROCESSING: 'bg-blue-100 text-blue-800', DONE: 'bg-green-100 text-green-800', FAILED: 'bg-red-100 text-red-800' };

  if (props.loading) {
    return html'<div class="bg-white rounded-xl shadow-sm overflow-hidden"><div class="p-6 space-y-4">${[1,2,3,4,5].map(function() { return html'<div class="h-12 bg-gray-100 rounded animate-pulse"></div>'; })}</div></div>';
  }

  if (!props.jobs || props.jobs.length === 0) {
    return html'<div class="bg-white rounded-xl shadow-sm p-12 text-center"><div class="text-4xl mb-4">📭</div><p class="text-gray-500">No jobs yet.</p><p class="text-gray-400 text-sm mt-1">Upload a file above to get started.</p></div>';
  }

  return html`<div class="bg-white rounded-xl shadow-sm overflow-hidden table-scroll">
    <table class="w-full min-w-[600px]">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Input</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Output</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-200">${props.jobs.map(function(job) { return html`<tr class="hover:bg-gray-50">
        <td class="px-6 py-4 text-sm font-mono text-gray-600">${job.id.slice(0,8)}...</td>
        <td class="px-6 py-4 text-sm text-gray-600">${(job.inputFormat || '').toUpperCase()}</td>
        <td class="px-6 py-4 text-sm text-gray-600">${(job.outputFormat || '').toUpperCase()}</td>
        <td class="px-6 py-4"><span class="px-2 py-1 text-xs rounded-full ${statusColors[job.status] || 'bg-gray-100'}">${job.status}</span></td>
        <td class="px-6 py-4 text-sm text-gray-500">${new Date(job.createdAt).toLocaleDateString()}</td>
        <td class="px-6 py-4">${job.status === 'DONE' && job.outputUrl ? html'<a href="${job.outputUrl}" target="_blank" class="text-indigo-600 hover:text-indigo-700 text-sm font-medium">Download</a>' : '—'}</td>
      </tr>`; })}</tbody>
    </table>
    ${props.totalPages > 1 ? html'<div class="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
      <span class="text-sm text-gray-500">Page ${props.page} of ${props.totalPages}</span>
      <div class="flex gap-2">
        <button onclick="${function() { props.onPageChange(props.page - 1); }}" disabled="${props.page <= 1}" class="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">← Previous</button>
        <button onclick="${function() { props.onPageChange(props.page + 1); }}" disabled="${props.page >= props.totalPages}" class="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">Next →</button>
      </div>
    </div>' : ''}
  </div>`;
}

// Sidebar
function Sidebar(props) {
  var user = Store.getUser();
  var isAdmin = user && user.role === 'admin';

  var nav = [
    { path: '/dashboard', icon: '📊', label: 'Dashboard' },
    { path: '/keys', icon: '🔑', label: 'API Key' },
    { path: '/billing', icon: '💳', label: 'Billing' },
  ];
  if (isAdmin) nav.push({ path: '/admin', icon: '⚙️', label: 'Admin' });

  return html`<aside class="w-64 bg-slate-900 min-h-screen p-6 flex flex-col text-white">
    <a href="#/dashboard" class="text-2xl font-bold mb-10">Zenvort</a>
    <nav class="flex-1 space-y-1">${nav.map(function(item) {
      var isActive = props.currentPath === item.path;
      return html'<a href="#${item.path}" class="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-white/10'}">
        <span>${item.icon}</span><span>${item.label}</span>
      </a>';
    })}</nav>
    <div class="pt-6 border-t border-white/10">
      <div class="px-4 py-2 text-sm text-gray-400 truncate mb-2">${user ? user.email : ''}</div>
      <button onclick="${function() { Store.clearAuth(); Router.navigate('/landing'); }}" class="flex items-center gap-3 px-4 py-3 w-full rounded-lg text-gray-300 hover:bg-white/10 transition-colors">
        <span>🚪</span><span>Sign out</span>
      </button>
    </div>
  </aside>`;
}

// Navbar
function Navbar() {
  var user = Store.getUser();
  return html`<nav class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
    <a href="#/dashboard" class="text-xl font-bold text-indigo-600">Zenvort</a>
    <div class="flex items-center gap-4">
      <span class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">💰 ${user ? user.credits : 0} credits</span>
      <span class="text-gray-600 text-sm hidden sm:block">${user ? user.email : ''}</span>
    </div>
  </nav>`;
}

// Layout shell
function Layout(props) {
  return html`<div class="flex min-h-screen">
    <${Sidebar} currentPath="${props.currentPath}" />
    <div class="flex-1 flex flex-col min-w-0">
      <${Navbar} />
      <main class="flex-1 overflow-auto">${props.children}</main>
    </div>
  </div>`;
}

// ============================================================
//  PAGES
// ============================================================

// ---- Landing ----
function Landing() {
  var plans = useState([]);
  var loadingPlans = useState(true);

  useEffect(function() {
    API.getPlans().then(function(data) { plans[1](data); loadingPlans[1](false); }).catch(function() { loadingPlans[1](false); });
  }, []);

  var features = [
    { icon: '🎬', title: 'FFmpeg', desc: 'Video and audio conversion — mp4, mov, avi, mkv, mp3, wav, and more.' },
    { icon: '📄', title: 'LibreOffice', desc: 'Document processing — pdf, docx, xlsx, pptx, and more.' },
    { icon: '⚡', title: 'BullMQ Queue', desc: 'Async processing with automatic retries. Handle thousands of jobs.' },
    { icon: '☁️', title: 'R2 Storage', desc: 'Files stored securely in Cloudflare R2 with automatic cleanup.' },
    { icon: '🔔', title: 'Webhooks', desc: 'Get notified instantly when conversions complete.' },
    { icon: '💳', title: 'Credit System', desc: 'Pay per conversion. No subscriptions, no expiry.' },
  ];

  return html`<div class="min-h-screen bg-white">
    <!-- Hero -->
    <section class="bg-gradient-to-br from-indigo-600 to-indigo-800 text-white">
      <nav class="container mx-auto px-6 py-6 flex justify-between items-center">
        <span class="text-2xl font-bold">Zenvort</span>
        <div class="flex gap-4">
          <a href="#/login" class="px-4 py-2 text-white/80 hover:text-white">Login</a>
          <a href="#/signup" class="px-5 py-2 bg-white text-indigo-600 rounded-lg font-semibold hover:bg-indigo-50">Get Started</a>
        </div>
      </nav>
      <div class="container mx-auto px-6 py-24 text-center">
        <h1 class="text-5xl font-bold mb-6">Convert any file.<br/><span class="text-indigo-200">Instantly. At scale.</span></h1>
        <p class="text-xl text-white/80 mb-10 max-w-2xl mx-auto">A developer-first file conversion API powered by FFmpeg and LibreOffice. Upload, convert, download.</p>
        <div class="flex gap-4 justify-center">
          <a href="#/signup" class="px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold text-lg hover:bg-indigo-50 shadow-lg">Get API Key — Free</a>
          <a href="/api-docs" class="px-8 py-4 border-2 border-white/30 text-white rounded-xl font-semibold text-lg hover:bg-white/10">Read Docs</a>
        </div>
      </div>
      <div class="h-16 bg-white rounded-t-[3rem]"></div>
    </section>

    <!-- How it works -->
    <section class="py-20 bg-gray-50">
      <div class="container mx-auto px-6">
        <h2 class="text-3xl font-bold text-center mb-16">How It Works</h2>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="bg-white rounded-2xl p-8 shadow-sm">
            <div class="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center text-2xl mb-6">📤</div>
            <h3 class="text-xl font-bold mb-3">1. Upload File</h3>
            <p class="text-gray-600 mb-4">POST your file to /jobs with your API key.</p>
            <pre class="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm overflow-x-auto"><code>curl -X POST https://api.zenvort.io/jobs -H "x-api-key: YOUR_KEY" -F "file=@video.mp4" -F "outputFormat=mp3"</code></pre>
          </div>
          <div class="bg-white rounded-2xl p-8 shadow-sm">
            <div class="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center text-2xl mb-6">⚙️</div>
            <h3 class="text-xl font-bold mb-3">2. Job Queued</h3>
            <p class="text-gray-600 mb-4">BullMQ picks up your job. FFmpeg or LibreOffice converts your file.</p>
            <pre class="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm"><code>{ "jobId": "abc123", "status": "PROCESSING" }</code></pre>
          </div>
          <div class="bg-white rounded-2xl p-8 shadow-sm">
            <div class="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center text-2xl mb-6">📥</div>
            <h3 class="text-xl font-bold mb-3">3. Get Result</h3>
            <p class="text-gray-600 mb-4">Webhook fires or poll /jobs/:id for the result URL.</p>
            <pre class="bg-gray-900 text-gray-100 rounded-lg p-4 text-sm"><code>{ "status": "DONE", "outputUrl": "..." }</code></pre>
          </div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="py-20">
      <div class="container mx-auto px-6">
        <h2 class="text-3xl font-bold text-center mb-16">Built for Developers</h2>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">${features.map(function(f) { return html`<div class="bg-gray-50 rounded-xl p-6 hover:bg-indigo-50 transition-colors">
          <div class="text-3xl mb-4">${f.icon}</div>
          <h3 class="text-lg font-bold mb-2">${f.title}</h3>
          <p class="text-gray-600">${f.desc}</p>
        </div>`; })}</div>
      </div>
    </section>

    <!-- Pricing -->
    <section class="py-20 bg-gray-50">
      <div class="container mx-auto px-6">
        <h2 class="text-3xl font-bold text-center mb-4">Pricing</h2>
        <p class="text-gray-600 text-center mb-12">Pay per conversion. Credits never expire.</p>
        ${loadingPlans[0] ? html'<div class="text-center py-12">Loading plans...</div>' : html`<div class="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          ${plans[0].map(function(plan, i) { return html`<div class="bg-white rounded-2xl p-8 shadow-sm border-2 ${i === 1 ? 'border-indigo-500 relative' : 'border-gray-100'}">
            ${i === 1 ? html'<div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</div>' : ''}
            <div class="flex items-baseline gap-2 mb-4">
              <span class="text-3xl font-bold text-indigo-600">${plan.credits}</span>
              <span class="text-gray-500">credits</span>
            </div>
            <div class="text-4xl font-bold mb-6">₹${plan.amount}</div>
            <p class="text-gray-500 mb-6 text-center">${plan.name}</p>
            <div class="inline-block px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium mb-6">Beta — Contact us</div>
          </div>`; })}
        </div>`}
      </div>
    </section>

    <!-- CTA -->
    <section class="py-20 bg-indigo-600 text-white text-center">
      <div class="container mx-auto px-6">
        <h2 class="text-3xl font-bold mb-4">Ready to convert?</h2>
        <p class="text-indigo-200 mb-8">Get your free API key and start converting files in minutes.</p>
        <a href="#/signup" class="inline-block px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold text-lg hover:bg-indigo-50 shadow-lg">Get Started Free</a>
      </div>
    </section>

    <!-- Footer -->
    <footer class="bg-gray-900 text-gray-400 py-12">
      <div class="container mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
        <span class="text-2xl font-bold text-white">Zenvort</span>
        <nav class="flex gap-6 text-sm">
          <a href="/api-docs" class="hover:text-white">Docs</a>
          <a href="https://github.com" class="hover:text-white">GitHub</a>
          <a href="#/privacy" class="hover:text-white">Privacy</a>
        </nav>
        <p class="text-sm">© ${new Date().getFullYear()} Zenvort</p>
      </div>
    </footer>
  </div>`;
}

// ---- Login ----
function Login() {
  var email = useState('');
  var password = useState('');
  var error = useState('');
  var loading = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    error[1]('');
    loading[1](true);
    API.login(email[0], password[0]).then(function(data) {
      Store.setAuth(data.apiKey, data.user);
      var returnTo = sessionStorage.getItem('returnTo') || '/dashboard';
      sessionStorage.removeItem('returnTo');
      Router.navigate(returnTo);
    }).catch(function(err) {
      error[1](err.message || 'Login failed');
    }).finally(function() { loading[1](false); });
  }

  return html`<div class="min-h-screen bg-gradient-to-br from-gray-50 to-indigo-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <a href="#/landing" class="text-4xl font-bold text-indigo-600">Zenvort</a>
        <p class="text-gray-500 mt-2">Sign in to your account</p>
      </div>
      <div class="bg-white rounded-2xl shadow-xl p-8">
        ${error[0] ? html'<div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">' + error[0] + '</div>' : ''}
        <form onsubmit="${handleSubmit}" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input type="email" value="${email[0]}" oninput="${function(e) { email[1](e.target.value); }}" placeholder="you@example.com" required class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input type="password" value="${password[0]}" oninput="${function(e) { password[1](e.target.value); }}" placeholder="••••••••" required class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          </div>
          <button type="submit" disabled="${loading[0]}" class="w-full py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            ${loading[0] ? html'<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg><span>Signing in...</span>' : 'Sign in'}
          </button>
        </form>
        <p class="text-center text-gray-500 mt-6 text-sm">Don't have an account? <a href="#/signup" class="text-indigo-600 font-medium hover:underline">Sign up</a></p>
      </div>
    </div>
  </div>`;
}

// ---- Signup ----
function Signup() {
  var email = useState('');
  var password = useState('');
  var confirm = useState('');
  var error = useState('');
  var loading = useState(false);

  function validate() {
    if (!email[0]) return 'Email is required';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email[0])) return 'Invalid email format';
    if (!password[0]) return 'Password is required';
    if (password[0].length < 8) return 'Password must be at least 8 characters';
    if (password[0] !== confirm[0]) return 'Passwords do not match';
    return null;
  }

  function handleSubmit(e) {
    e.preventDefault();
    var err = validate();
    if (err) { error[1](err); return; }
    error[1]('');
    loading[1](true);
    API.signup(email[0], password[0]).then(function() {
      showToast('Account created! Please sign in.');
      Router.navigate('/login');
    }).catch(function(err) {
      error[1](err.message || 'Signup failed');
    }).finally(function() { loading[1](false); });
  }

  return html`<div class="min-h-screen bg-gradient-to-br from-gray-50 to-indigo-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <a href="#/landing" class="text-4xl font-bold text-indigo-600">Zenvort</a>
        <p class="text-gray-500 mt-2">Create your free account</p>
      </div>
      <div class="bg-white rounded-2xl shadow-xl p-8">
        ${error[0] ? html'<div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">' + error[0] + '</div>' : ''}
        <form onsubmit="${handleSubmit}" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input type="email" value="${email[0]}" oninput="${function(e) { email[1](e.target.value); }}" placeholder="you@example.com" required class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <input type="password" value="${password[0]}" oninput="${function(e) { password[1](e.target.value); }}" placeholder="Min 8 characters" required class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
            <input type="password" value="${confirm[0]}" oninput="${function(e) { confirm[1](e.target.value); }}" placeholder="••••••••" required class="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          </div>
          <button type="submit" disabled="${loading[0]}" class="w-full py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            ${loading[0] ? html'<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg><span>Creating account...</span>' : 'Create account'}
          </button>
        </form>
        <p class="text-center text-gray-500 mt-6 text-sm">Already have an account? <a href="#/login" class="text-indigo-600 font-medium hover:underline">Sign in</a></p>
      </div>
    </div>
  </div>`;
}

// ---- Dashboard ----
function Dashboard() {
  var usage = useState(null);
  var loadingUsage = useState(true);
  var jobs = useState([]);
  var loadingJobs = useState(true);
  var page = useState(1);
  var totalPages = useState(1);
  var file = useState(null);
  var outputFormat = useState('pdf');
  var submitting = useState(false);
  var submitError = useState('');

  var formats = ['pdf', 'docx', 'mp4', 'mp3', 'png', 'jpg', 'webm', 'gif', 'txt', 'xlsx', 'pptx'];

  function fetchUsage() {
    API.getUsage().then(function(data) { usage[1](data); }).catch(function() {}).finally(function() { loadingUsage[1](false); });
  }

  function fetchJobs(p) {
    p = p || 1;
    loadingJobs[1](true);
    API.getJobs(p, 20).then(function(data) {
      jobs[1](data.jobs || []);
      totalPages[1](Math.ceil(data.total / 20));
      page[1](p);
    }).catch(function() {}).finally(function() { loadingJobs[1](false); });
  }

  useEffect(function() { fetchUsage(); fetchJobs(1); }, []);

  useEffect(function() {
    var hasActive = jobs[0] && jobs[0].some(function(j) { return j.status === 'PENDING' || j.status === 'PROCESSING'; });
    if (!hasActive || loadingJobs[0]) return;
    var timer = setTimeout(function() { fetchJobs(page[0]); }, 5000);
    return function() { clearTimeout(timer); };
  }, [jobs[0], page[0], loadingJobs[0]]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!file[0]) { submitError[1]('Please select a file'); return; }
    submitting[1](true);
    submitError[1]('');
    API.createJob(file[0], outputFormat[0]).then(function(result) {
      showToast('Job queued — ID: ' + result.jobId.slice(0,8) + '...');
      file[1](null);
      document.getElementById('file-input').value = '';
      fetchJobs(1);
      fetchUsage();
    }).catch(function(err) {
      submitError[1](err.message || 'Failed to submit job');
    }).finally(function() { submitting[1](false); });
  }

  return html`<div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
    <p class="text-gray-500 mb-8">Welcome back! Here's your conversion overview.</p>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <${StatCard} title="Credits Remaining" value="${loadingUsage[0] ? '...' : (usage[0] ? usage[0].credits : 0)}" icon="💰" />
      <${StatCard} title="Total Jobs" value="${loadingUsage[0] ? '...' : (usage[0] ? usage[0].totalJobs : 0)}" icon="📁" />
      <${StatCard} title="Jobs Today" value="${loadingUsage[0] ? '...' : (usage[0] ? usage[0].jobsToday : 0)}" icon="📅" />
      <${StatCard} title="Success Rate" value="${loadingUsage[0] ? '...' : (usage[0] ? usage[0].successRate + '%' : '0%')}" icon="✅" />
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
      <h2 class="text-lg font-semibold mb-4">New Conversion</h2>
      ${submitError[0] ? html'<div class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">' + submitError[0] + '</div>' : ''}
      <form onsubmit="${handleSubmit}" class="flex flex-wrap gap-4 items-end">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm font-medium text-gray-700 mb-2">Select file</label>
          <input id="file-input" type="file" accept="*/*" onchange="${function(e) { file[1](e.target.files[0]); }}" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
        </div>
        <div class="w-40">
          <label class="block text-sm font-medium text-gray-700 mb-2">Output format</label>
          <select value="${outputFormat[0]}" onchange="${function(e) { outputFormat[1](e.target.value); }}" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
            ${formats.map(function(f) { return html'<option value="${f}" selected="${f === outputFormat[0]}">' + f.toUpperCase() + '</option>'; })}
          </select>
        </div>
        <button type="submit" disabled="${submitting[0] || !file[0]}" class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
          ${submitting[0] ? html'<svg class="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg><span>Converting...</span>' : html'<span>⚡</span><span>Convert</span>'}
        </button>
      </form>
    </div>

    <div>
      <h2 class="text-lg font-semibold mb-4">Recent Jobs</h2>
      <${JobTable} jobs="${jobs[0]}" loading="${loadingJobs[0]}" page="${page[0]}" totalPages="${totalPages[0]}" onPageChange="${fetchJobs}" />
    </div>
  </div>`;
}

// ---- ApiKey ----
function ApiKey() {
  var user = useState(null);
  var loading = useState(true);
  var revealed = useState(false);
  var webhookUrl = useState('');
  var webhookInput = useState('');
  var updating = useState(false);

  useEffect(function() {
    API.getMe().then(function(data) {
      user[1](data);
      webhookUrl[1](data.webhookUrl || '');
      webhookInput[1](data.webhookUrl || '');
    }).catch(function() {}).finally(function() { loading[1](false); });
  }, []);

  function updateWebhook(e) {
    e.preventDefault();
    updating[1](true);
    API.updateWebhook(webhookInput[0]).then(function() {
      webhookUrl[1](webhookInput[0]);
      showToast('Webhook URL updated');
    }).catch(function(err) { showToast(err.message || 'Failed to update webhook', 'error'); }).finally(function() { updating[1](false); });
  }

  var apiKey = Store.getApiKey();

  if (loading[0]) {
    return html`<div class="p-6 max-w-2xl mx-auto"><div class="h-8 bg-gray-200 rounded w-48 mb-8 animate-pulse"></div><div class="h-40 bg-gray-200 rounded-xl animate-pulse"></div></div>`;
  }

  return html`<div class="p-6 max-w-2xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">API Key</h1>
    <p class="text-gray-500 mb-8">Your authentication key for API requests.</p>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
      <h2 class="text-lg font-semibold mb-4">Your API Key</h2>
      <div class="flex items-center gap-3 mb-4">
        <code class="flex-1 bg-gray-100 px-4 py-3 rounded-lg font-mono text-sm break-all select-all">${revealed[0] ? apiKey : apiKey.slice(0,8) + '••••••••••••••••'}</code>
        <button onclick="${function() { revealed[1](!revealed[0]); }}" class="px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-sm">${revealed[0] ? 'Hide' : 'Reveal'}</button>
        <button onclick="${function() { navigator.clipboard.writeText(apiKey); showToast('Copied!'); }}" class="px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm">Copy</button>
      </div>
      <div class="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p class="text-blue-800 text-sm">Use this key as <code class="bg-blue-100 px-2 py-1 rounded">Authorization: Bearer &lt;key&gt;</code> on all API requests.</p>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 class="text-lg font-semibold mb-4">Webhook URL</h2>
      <p class="text-gray-500 text-sm mb-4">Receive notifications when jobs complete.</p>
      ${webhookUrl[0] ? html'<p class="text-sm text-gray-600 mb-4">Current: <span class="font-mono bg-gray-100 px-2 py-1 rounded">' + webhookUrl[0] + '</span></p>' : ''}
      <form onsubmit="${updateWebhook}" class="flex gap-3">
        <input type="url" value="${webhookInput[0]}" oninput="${function(e) { webhookInput[1](e.target.value); }}" placeholder="https://your-server.com/webhook" class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
        <button type="submit" disabled="${updating[0]}" class="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50">${updating[0] ? 'Saving...' : 'Save'}</button>
      </form>
    </div>
  </div>`;
}

// ---- Billing ----
function Billing() {
  var usage = useState(null);
  var loadingUsage = useState(true);
  var plans = useState([]);
  var loadingPlans = useState(true);
  var transactions = useState([]);
  var loadingTransactions = useState(true);

  useEffect(function() {
    API.getUsage().then(function(d) { usage[1](d); loadingUsage[1](false); }).catch(function() { loadingUsage[1](false); });
    API.getPlans().then(function(d) { plans[1](d); loadingPlans[1](false); }).catch(function() { loadingPlans[1](false); });
    API.getTransactions().then(function(d) { transactions[1](d.logs || []); loadingTransactions[1](false); }).catch(function() { loadingTransactions[1](false); });
  }, []);

  function formatDate(d) { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
  function reasonLabel(r) { var map = { signup: 'Signup bonus', conversion: 'Conversion', purchase: 'Purchase', manual_add: 'Credit added', manual_deduct: 'Credit deducted' }; return map[r] || r; }

  return html`<div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">Billing</h1>
    <p class="text-gray-500 mb-8">Manage your credits and view transaction history.</p>

    <div class="bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-2xl p-8 text-white mb-8">
      <p class="text-indigo-200 text-sm font-medium mb-2">Available Credits</p>
      <p class="text-5xl font-bold mb-4">${loadingUsage[0] ? '...' : (usage[0] ? usage[0].credits.toLocaleString() : '0')}</p>
      <p class="text-indigo-200 text-sm">${loadingUsage[0] ? '' : (usage[0] ? usage[0].totalJobs + ' total conversions · ' + usage[0].successRate + '% success rate' : '')}</p>
    </div>

    <section class="mb-12">
      <h2 class="text-xl font-bold text-gray-900 mb-6">Credit Packs</h2>
      ${loadingPlans[0] ? html'<div class="text-center py-8">Loading...</div>' : html`<div class="grid md:grid-cols-3 gap-6">
        ${plans[0].map(function(plan, i) { return html`<div class="bg-white rounded-xl shadow-sm border-2 ${i === 1 ? 'border-indigo-500 relative' : 'border-gray-100'} p-6">
          ${i === 1 ? html'<div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-full">POPULAR</div>' : ''}
          <h3 class="text-lg font-bold mb-2">${plan.name}</h3>
          <div class="flex items-baseline gap-2 mb-4">
            <span class="text-3xl font-bold text-indigo-600">${plan.credits}</span>
            <span class="text-gray-500">credits</span>
          </div>
          <div class="text-3xl font-bold text-gray-900 mb-6">₹${plan.amount}</div>
          <div class="inline-block px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium">Beta — Contact us</div>
        </div>`; })}
      </div>`}
    </section>

    <section>
      <h2 class="text-xl font-bold text-gray-900 mb-6">Transaction History</h2>
      <div class="bg-white rounded-xl shadow-sm overflow-hidden table-scroll">
        ${loadingTransactions[0] ? html'<div class="p-6 space-y-4">' + [1,2,3].map(function() { return html'<div class="h-12 bg-gray-100 rounded animate-pulse"></div>'; }).join('') + '</div>' :
          transactions[0].length === 0 ? html'<div class="p-12 text-center"><div class="text-4xl mb-4">📋</div><p class="text-gray-500">No transactions yet.</p></div>' : html`<table class="w-full min-w-[500px]">
            <thead class="bg-gray-50">
              <tr><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Job ID</th></tr>
            </thead>
            <tbody class="divide-y divide-gray-200">${transactions[0].map(function(tx) { return html`<tr class="hover:bg-gray-50">
              <td class="px-6 py-4 text-sm text-gray-600">${formatDate(tx.createdAt)}</td>
              <td class="px-6 py-4 text-sm font-medium text-gray-900">${reasonLabel(tx.reason)}</td>
              <td class="px-6 py-4 text-sm ${tx.amount > 0 ? 'text-green-600' : 'text-red-600'} font-semibold">${tx.amount > 0 ? '+' : ''}${tx.amount}</td>
              <td class="px-6 py-4 text-sm font-mono text-gray-500">${tx.jobId ? tx.jobId.slice(0,8) + '...' : '—'}</td>
            </tr>`; })}</tbody>
          </table>`}
      </div>
    </section>
  </div>`;
}

// ---- Admin ----
function Admin() {
  var stats = useState(null);
  var loadingStats = useState(true);
  var users = useState([]);
  var loadingUsers = useState(true);
  var page = useState(1);
  var total = useState(0);
  var adjustingUser = useState(null);
  var adjustAmount = useState('');
  var adjustError = useState('');

  function fetchStats() {
    API.getAdminStats().then(function(data) { stats[1](data); }).catch(function() {}).finally(function() { loadingStats[1](false); });
  }

  function fetchUsers(p) {
    p = p || 1;
    loadingUsers[1](true);
    API.getAdminUsers(p).then(function(data) {
      users[1](data.users || []);
      total[1](data.total);
      page[1](p);
    }).catch(function() {}).finally(function() { loadingUsers[1](false); });
  }

  useEffect(function() { fetchStats(); fetchUsers(1); }, []);

  function handleAdjustCredits(userId) {
    var amt = parseInt(adjustAmount[0]);
    if (isNaN(amt) || amt === 0) { adjustError[1]('Enter a number'); return; }
    adjustError[1]('');
    API.adjustCredits(userId, amt).then(function() {
      showToast('Credits updated');
      adjustingUser[1](null);
      adjustAmount[1]('');
      fetchUsers(page[0]);
    }).catch(function(err) { adjustError[1](err.message); });
  }

  function formatDate(d) { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
  var totalPages = Math.ceil(total[0] / 20);

  return html`<div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">Admin Panel</h1>
    <p class="text-gray-500 mb-8">Platform management and monitoring.</p>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <${StatCard} title="Total Users" value="${loadingStats[0] ? '...' : (stats[0] ? stats[0].totalUsers : 0)}" icon="👥" />
      <${StatCard} title="Total Jobs" value="${loadingStats[0] ? '...' : (stats[0] ? stats[0].totalJobs : 0)}" icon="📁" />
      <${StatCard} title="Jobs Today" value="${loadingStats[0] ? '...' : (stats[0] ? stats[0].jobsToday : 0)}" icon="📅" />
      <${StatCard} title="Active Jobs" value="${loadingStats[0] ? '...' : (stats[0] ? stats[0].activeJobs : 0)}" icon="⚡" />
    </div>

    <div class="bg-white rounded-xl shadow-sm overflow-hidden table-scroll">
      <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 class="text-lg font-semibold">Users</h2>
        <button onclick="${function() { fetchUsers(page[0]); }}" class="text-sm text-indigo-600 hover:underline">↻ Refresh</button>
      </div>

      ${loadingUsers[0] ? html'<div class="p-6 space-y-4">' + [1,2,3,4,5].map(function() { return html'<div class="h-12 bg-gray-100 rounded animate-pulse"></div>'; }).join('') + '</div>' : html`<table class="w-full min-w-[700px]">
        <thead class="bg-gray-50">
          <tr><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Credits</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Jobs</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Joined</th><th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th></tr>
        </thead>
        <tbody class="divide-y divide-gray-200">${users[0].map(function(u) { return html`<tr class="hover:bg-gray-50">
          <td class="px-6 py-4 text-sm font-medium text-gray-900 break-all">${u.email}</td>
          <td class="px-6 py-4 text-sm text-gray-600">${u.credits}</td>
          <td class="px-6 py-4 text-sm text-gray-600">${u._count ? u._count.jobs : 0}</td>
          <td class="px-6 py-4"><span class="px-2 py-1 text-xs rounded-full ${u.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}">${u.role}</span></td>
          <td class="px-6 py-4 text-sm text-gray-500">${formatDate(u.createdAt)}</td>
          <td class="px-6 py-4">${adjustingUser[0] === u.id ? html`<div class="flex items-center gap-2">
            <input type="number" value="${adjustAmount[0]}" oninput="${function(e) { adjustAmount[1](e.target.value); }}" placeholder="Amount" class="w-24 px-2 py-1 border border-gray-300 rounded text-sm" />
            <button onclick="${function() { handleAdjustCredits(u.id); }}" class="px-3 py-1 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700">Apply</button>
            <button onclick="${function() { adjustingUser[1](null); }}" class="px-3 py-1 border border-gray-300 text-sm rounded hover:bg-gray-50">Cancel</button>
            ${adjustError[0] && adjustingUser[0] === u.id ? html'<span class="text-red-600 text-xs">' + adjustError[0] + '</span>' : ''}
          </div>` : html'<button onclick="${function() { adjustingUser[1](u.id); adjustAmount[1](''); adjustError[1](''); }}" class="text-indigo-600 hover:text-indigo-700 text-sm font-medium">Adjust Credits</button>'}
          </td>
        </tr>`; })}</tbody>
      </table>

      ${totalPages > 1 ? html'<div class="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
        <span class="text-sm text-gray-500">${total[0]} total users · Page ${page[0]} of ${totalPages}</span>
        <div class="flex gap-2">
          <button onclick="${function() { fetchUsers(page[0] - 1); }}" disabled="${page[0] <= 1}" class="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">← Previous</button>
          <button onclick="${function() { fetchUsers(page[0] + 1); }}" disabled="${page[0] >= totalPages}" class="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">Next →</button>
        </div>
      </div>' : ''}`}
    </div>
  </div>`;
}

// ============================================================
//  APP ROOT
// ============================================================

function App() {
  var component = useState(null);
  var path = useState('/');

  useEffect(function() {
    Router.register('/landing', Landing);
    Router.register('/login', Login);
    Router.register('/signup', Signup);
    Router.register('/dashboard', Dashboard);
    Router.register('/keys', ApiKey);
    Router.register('/billing', Billing);
    Router.register('/admin', Admin);

    Router.onRoute(function(comp, p) {
      component[1](function() { return comp; });
      path[1](p);
    });

    Router.init();
  }, []);

  if (!component[0]) {
    return html'<div class="min-h-screen flex items-center justify-center"><div class="text-gray-500">Loading...</div></div>';
  }

  var publicRoutes = ['/landing', '/login', '/signup'];
  if (publicRoutes.indexOf(path[0]) !== -1) {
    var Comp = component[0];
    return html`<${Comp} key="${path[0]}" />`;
  }

  return html`<${Layout} currentPath="${path[0]}"><${component[0]} key="${path[0]}" /></${Layout}>`;
}

// Render
render(h(App), document.getElementById('app'));
</script>
</body>
