import { createContext, useContext, useReducer, useEffect } from 'react'

const AuthContext = createContext(null)
const ThemeContext = createContext(null)

// ── Auth State ─────────────────────────────────────────────
const initialAuth = {
  user: null,
  isAuthenticated: false,
  credits: 0,
  apiKey: null,
}

function authReducer(state, action) {
  switch (action.type) {
    case 'LOGIN':
      return { ...state, user: action.payload, isAuthenticated: true }
    case 'LOGOUT':
      return initialAuth
    case 'SET_CREDITS':
      return { ...state, credits: action.payload }
    case 'SET_API_KEY':
      return { ...state, apiKey: action.payload }
    default:
      return state
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialAuth)

  useEffect(() => {
    const stored = localStorage.getItem('zenvort_user')
    if (stored) {
      try {
        const user = JSON.parse(stored)
        dispatch({ type: 'LOGIN', payload: user })
        dispatch({ type: 'SET_CREDITS', payload: user.credits || 0 })
        dispatch({ type: 'SET_API_KEY', payload: user.apiKey || null })
      } catch {}
    }
  }, [])

  return <AuthContext.Provider value={{ state, dispatch }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

// ── Theme State ─────────────────────────────────────────────
export function ThemeProvider({ children }) {
  const [dark, setDark] = useReducer((s, v) => (v === undefined ? !s : v), false)

  useEffect(() => {
    const stored = localStorage.getItem('zenvort_theme')
    if (stored === 'dark') {
      document.documentElement.classList.add('dark')
      setDark(true)
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [])

  const toggleDark = () => {
    const next = !dark
    setDark(next)
    if (next) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('zenvort_theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('zenvort_theme', 'light')
    }
  }

  return <ThemeContext.Provider value={{ dark, toggleDark }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  return useContext(ThemeContext)
}

// ── Jobs State ─────────────────────────────────────────────
const JobsContext = createContext(null)

const initialJobsState = { jobs: [], loading: false }

function jobsReducer(state, action) {
  switch (action.type) {
    case 'SET_JOBS':
      return { ...state, jobs: action.payload }
    case 'ADD_JOB':
      return { ...state, jobs: [action.payload, ...state.jobs] }
    case 'UPDATE_JOB':
      return {
        ...state,
        jobs: state.jobs.map(j => (j.id === action.payload.id ? { ...j, ...action.payload } : j)),
      }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    default:
      return state
  }
}

export function JobsProvider({ children }) {
  const [state, dispatch] = useReducer(jobsReducer, initialJobsState)
  return <JobsContext.Provider value={{ state, dispatch }}>{children}</JobsContext.Provider>
}

export function useJobs() {
  return useContext(JobsContext)
}