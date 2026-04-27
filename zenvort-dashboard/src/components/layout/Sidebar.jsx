import { useAuth } from '@/lib/store'
import { useNavigate, useLocation } from 'react-router-dom'

const navItems = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'API Key', path: '/api-key' },
  { label: 'Billing', path: '/billing' },
  { label: 'Admin', path: '/admin' },
]

export default function Sidebar() {
  const { state } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const user = JSON.parse(localStorage.getItem('zenvort_user') || '{}')

  const handleLogout = () => {
    localStorage.removeItem('zenvort_api_key')
    localStorage.removeItem('zenvort_user')
    navigate('/login')
  }

  // Only show Admin nav item for admin users
  const visibleNavItems = navItems.filter(item => {
    if (item.path === '/admin' && user.role !== 'admin') return false
    return true
  })

  return (
    <div className="w-[180px] bg-slate-900 flex flex-col p-4 flex-shrink-0 min-h-screen">
      {/* Logo */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-[18px] h-[18px] bg-primary rounded flex-shrink-0" style={{ width: 18, height: 18 }} />
        <span className="text-white text-[13px] font-medium">Zenvort</span>
      </div>

      {/* Nav */}
      <div className="flex flex-col gap-1">
        {visibleNavItems.map(item => {
          const active = location.pathname === item.path
          return (
            <div
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`px-3 py-2 rounded cursor-pointer text-[12px] transition-colors ${
                active
                  ? 'bg-primary/15 border-l-2 border-primary text-primary font-medium'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
              style={{ paddingLeft: active ? 10 : 12 }}
            >
              {item.label}
            </div>
          )
        })}
      </div>

      {/* Email */}
      <div className="mt-auto text-[11px] text-slate-600 mb-2">
        {state.user?.email || 'user@example.com'}
      </div>

      {/* Sign out */}
      <div
        onClick={handleLogout}
        className="px-3 py-1.5 text-[11px] text-slate-500 border border-slate-800 rounded cursor-pointer text-center hover:bg-slate-800 transition-colors"
      >
        Sign out
      </div>
    </div>
  )
}