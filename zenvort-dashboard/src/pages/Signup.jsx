import { BASE_URL } from '../lib/api.js';
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/store'

export default function Signup() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { dispatch } = useAuth()
  const navigate = useNavigate()

  const handleSignup = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (password !== confirmPassword) throw new Error('Passwords do not match')
      if (password.length < 8) throw new Error('Password must be at least 8 characters')

      const res = await fetch(BASE_URL + '/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Signup failed')

      localStorage.setItem('zenvort_api_key', data.apiKey)
      localStorage.setItem('zenvort_user', JSON.stringify(data.user))
      dispatch({ type: 'LOGIN', payload: data.user })
      dispatch({ type: 'SET_API_KEY', payload: data.apiKey })
      dispatch({ type: 'SET_CREDITS', payload: data.user.credits })
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
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

        {error && (
          <div className="mb-3 px-3 py-2 bg-red-50 border border-red-200 rounded-[6px] text-[12px] text-red-600">
            {error}
          </div>
        )}

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
          <div className="mb-3">
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
          <div className="mb-5">
            <label className="text-[11px] font-medium text-text-secondary mb-1.5 block">Confirm password</label>
            <input
              type={showPw ? 'text' : 'password'}
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full border border-border rounded-[6px] px-3 py-2 text-[12px] text-text-tertiary bg-white placeholder:text-text-tertiary focus:outline-none focus:ring-1 focus:ring-primary transition-colors dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-white text-[13px] py-2.5 rounded-[6px] font-medium cursor-pointer hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-[11px] text-text-tertiary mt-4">
          Already have an account? <span className="text-primary cursor-pointer hover:underline" onClick={() => navigate('/login')}>Sign in</span>
        </p>
      </div>
    </div>
  )
}