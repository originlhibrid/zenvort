import { useNavigate } from 'react-router-dom'
import { useTheme } from '@/lib/store'
import { Sun, Moon } from 'lucide-react'
import { cn } from '@/lib/utils'

const plans = [
  {
    name: 'Starter',
    price: '₹199',
    credits: '500',
    features: ['500 conversions', '28 input formats', 'Webhook support', 'REST API access'],
    cta: 'Get started',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₹599',
    credits: '2,000',
    features: ['2000 conversions', '28 input formats', 'Webhook support', 'REST API access'],
    cta: 'Get started',
    highlight: true,
  },
  {
    name: 'Enterprise',
    price: '₹1,999',
    credits: '10,000',
    features: ['10000 conversions', '28 input formats', 'Webhook support', 'REST API access'],
    cta: 'Get started',
    highlight: false,
  },
]

export default function Landing() {
  const { dark, toggleDark } = useTheme()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">

      {/* ── Navbar ── */}
      <div className="sticky top-0 z-50 bg-white/90 dark:bg-slate-950/90 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-3.5">
          {/* Logo */}
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-[22px] h-[22px] bg-indigo-500 rounded-[6px] flex-shrink-0" style={{ width: 22, height: 22 }} />
            <span className="text-[15px] font-medium text-slate-900 dark:text-white">Zenvort</span>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <span
              className="text-[13px] text-slate-700 dark:text-slate-200 cursor-pointer hover:text-slate-900 dark:hover:text-white transition-colors"
              onClick={() => navigate('/login')}
            >
              Login
            </span>
            <div
              className="bg-indigo-500 text-white text-[12px] px-3.5 py-1.5 rounded-[6px] font-medium cursor-pointer hover:bg-indigo-600 transition-colors"
              onClick={() => navigate('/signup')}
            >
              Get Started
            </div>

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
      </div>

      {/* ── Hero ── */}
      <section className="px-6 py-12 text-center bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800">
        {/* Beta badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary mb-5">
          <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
          Beta — 100 free credits · No card needed · Launch pricing coming soon
        </div>

        {/* Heading */}
        <h1 className="text-[32px] font-medium text-slate-900 dark:text-white leading-tight mb-3">
          Convert any file.<br />
          <span className="text-indigo-500">One API call.</span>
        </h1>

        {/* Subtext */}
        <p className="text-[14px] text-slate-600 dark:text-slate-300 max-w-[420px] mx-auto mb-7 leading-relaxed">
          28 formats — video, audio, images, documents. Powered by FFmpeg, LibreOffice, PyMuPDF and Pillow. Store on Cloudflare R2.
        </p>

        {/* CTAs */}
        <div className="flex gap-2.5 justify-center mb-3">
          <div
            className="bg-indigo-500 text-white text-[13px] px-5 py-2.5 rounded-[8px] font-medium cursor-pointer hover:bg-indigo-600 transition-colors"
            onClick={() => navigate('/signup')}
          >
            Start converting free
          </div>
          <div
            className="border-2 border-slate-800 dark:border-slate-300 text-slate-800 dark:text-slate-200 text-[13px] px-5 py-2.5 rounded-[8px] cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            onClick={() => {}}
          >
            See how it works
          </div>
        </div>

        <div className="text-[11px] text-slate-500 dark:text-slate-500">No credit card required</div>
      </section>

      {/* ── Social proof bar ── */}
      <section className="grid grid-cols-4 bg-slate-50 dark:bg-slate-900 border-y border-slate-200 dark:border-slate-700">
        {[
          { value: '28',     label: 'Input formats' },
          { value: '156',    label: 'Conversion routes' },
          { value: '~10s',   label: 'Avg conversion time' },
          { value: '100%',   label: 'Secure — files auto-deleted' },
        ].map((item, i) => (
          <div
            key={i}
            className={`px-4 py-3.5 text-center ${i < 3 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}
          >
            <div className={`font-medium ${i === 0 ? 'text-indigo-500 text-[16px] font-semibold' : 'text-slate-900 dark:text-white text-[13px]'}`}>
              {item.value}
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">{item.label}</div>
          </div>
        ))}
      </section>

      {/* ── Beta pricing section ── */}
      <section className="px-6 py-16 bg-slate-50 dark:bg-slate-900 border-y border-slate-200 dark:border-slate-700">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-green-500/30 bg-green-500/10 px-4 py-2 text-sm text-green-400 mb-6">
            <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
            Free during beta
          </div>
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-3">
            Free while we're in beta
          </h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            Sign up now and get 100 free credits. No credit card required.
            Pricing will be introduced when we launch publicly.
          </p>
          <a href="/signup">
            <button className="px-8 py-3 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition">
              Get started free →
            </button>
          </a>
          <p className="text-xs text-muted-foreground mt-4">
            Already have an account? <a href="/login" className="underline">Sign in</a>
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-indigo-50 dark:bg-slate-900 border-t-2 border-indigo-200 dark:border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between max-w-[700px] mx-auto">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-indigo-600 rounded" />
            <span className="text-[12px] font-semibold text-indigo-700 dark:text-indigo-300">Zenvort</span>
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-500">© 2026 Zenvort. All rights reserved.</span>
        </div>
      </footer>

    </div>
  )
}