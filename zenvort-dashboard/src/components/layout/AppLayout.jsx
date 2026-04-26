import Sidebar from './Sidebar'
import { useAuth, useTheme } from '@/lib/store'
import { Sun, Moon } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function AppLayout({ children }) {
  const { state } = useAuth()
  const { dark, toggleDark } = useTheme()

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <div className="flex items-center justify-between px-5 py-2.5 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
          <span className="text-[13px] font-medium text-slate-900 dark:text-white">Dashboard</span>
          <div className="flex items-center gap-2">
            {/* Credits badge */}
            <div className="px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 text-[11px] text-amber-800 dark:text-amber-400 font-medium">
              {state.credits} credits
            </div>
            {/* Email */}
            <span className="text-[11px] text-slate-500 dark:text-slate-400">{state.user?.email}</span>

            {/* Dark mode toggle — pill with sun/moon */}
            <button
              onClick={toggleDark}
              className={cn(
                'relative inline-flex items-center w-14 h-7 rounded-full border-2 transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2',
                dark
                  ? 'bg-indigo-600 border-indigo-400'
                  : 'bg-slate-200 border-slate-400'
              )}
              aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              <span
                className={cn(
                  'inline-block w-5 h-5 bg-white rounded-full shadow-sm transform transition-transform duration-300',
                  dark ? 'translate-x-7' : 'translate-x-1'
                )}
              />
              <Sun
                size={12}
                className={cn(
                  'absolute transition-opacity duration-300',
                  dark ? 'opacity-30 text-indigo-200 left-1.5' : 'opacity-100 text-amber-500 left-1.5'
                )}
              />
              <Moon
                size={12}
                className={cn(
                  'absolute transition-opacity duration-300',
                  dark ? 'opacity-100 text-white right-1.5' : 'opacity-30 text-slate-400 right-1.5'
                )}
              />
            </button>
          </div>
        </div>
        {/* Content */}
        <div className="flex-1 p-5 flex flex-col gap-4">
          {children}
        </div>
      </div>
    </div>
  )
}