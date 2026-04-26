import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/store'

export default function Signup() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const { dispatch } = useAuth()
  const navigate = useNavigate()

  const handleSignup = (e) => {
    e.preventDefault()
    const mockUser = {
      name,
      email,
      credits: 100,
      apiKey: 'zv_live_new_key_' + Math.random().toString(36).slice(2),
    }
    localStorage.setItem('zenvort_user', JSON.stringify(mockUser))
    localStorage.setItem('zenvort_token', 'demo_token')
    dispatch({ type: 'LOGIN', payload: mockUser })
    dispatch({ type: 'SET_CREDITS', payload: 100 })
    dispatch({ type: 'SET_API_KEY', payload: mockUser.apiKey })
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-6">
      <div className="w-[340px] bg-white border border-border rounded-[10px] p-7 dark:bg-slate-900 dark:border-slate-800">
        <div className="flex items-center gap-2 mb-6 justify-center">
          <div className="w-[20px] h-[20px] bg-primary rounded-[5px] flex-shrink-0" style={{ width: 20, height: 20 }} />
          <span className="text-[15px] font-medium text-text-primary">Zenvort</span>
        </div>

        <h2 className="text-[16px] font-medium text-text-primary mb-1">Create your account</h2>
        <p className="text-[12px] text-text-tertiary mb-5">Start with 100 free credits</p>

        <form onSubmit={handleSignup}>
          <div className="mb-3">
            <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Full name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Jane Doe"
              className="w-full border border-border rounded-[6px] px-3 py-2 text-[12px] text-text-tertiary bg-white placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-primary transition-colors dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300"
              required
            />
          </div>
          <div className="mb-3">
            <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full border border-border rounded-[6px] px-3 py-2 text-[12px] text-text-tertiary bg-white placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-primary transition-colors dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300"
              required
            />
          </div>
          <div className="mb-5">
            <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Password</label>
            <div className="flex items-center border border-border rounded-[6px] px-3 py-2 gap-2 bg-white dark:bg-slate-800 dark:border-slate-700">
              <input
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="flex-1 text-[12px] text-text-tertiary bg-transparent placeholder:text-text-tertiary focus:outline-none dark:text-slate-300"
                required
              />
              <span
                className="text-[11px] text-text-tertiary cursor-pointer hover:text-text-secondary"
                onClick={() => setShowPw(!showPw)}
              >
                {showPw ? 'hide' : 'show'}
              </span>
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-primary text-white text-[13px] py-2.5 rounded-[6px] font-medium cursor-pointer hover:bg-primary/90 transition-colors"
          >
            Create account
          </button>
        </form>

        <p className="text-center text-[11px] text-text-tertiary mt-4">
          Already have an account? <span className="text-primary cursor-pointer hover:underline" onClick={() => navigate('/login')}>Sign in</span>
        </p>
      </div>
    </div>
  )
}