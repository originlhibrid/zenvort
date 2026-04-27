import { BASE_URL } from '../lib/api.js';
import AppLayout from '@/components/layout/AppLayout'
import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/store'

export default function Billing() {
  const { state } = useAuth()
  const [usage, setUsage] = useState(null)

  useEffect(() => {
    fetch(BASE_URL + '/billing/usage', {
      headers: { Authorization: `Bearer ${localStorage.getItem('zenvort_api_key')}` },
    })
      .then(r => r.json())
      .then(data => { if (data.credits !== undefined) setUsage(data) })
      .catch(() => {})
  }, [])

  const credits = usage?.credits ?? state.credits ?? 0

  return (
    <AppLayout>
      <div className="max-w-[600px]">
        {/* Beta plan card */}
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <div className="text-4xl mb-4">🎉</div>
          <h2 className="text-xl font-bold text-text-primary mb-2">
            You're on the free beta plan
          </h2>
          <p className="text-text-tertiary text-sm mb-6">
            Enjoy unlimited access during our beta period.
            You started with 100 credits and earn more by using the platform.
            Paid plans will be available at launch.
          </p>
          <div className="rounded-lg border border-primary/20 bg-primary/5 px-6 py-4 mb-6">
            <div className="text-3xl font-bold text-primary mb-1">{credits}</div>
            <div className="text-sm text-text-tertiary">credits remaining</div>
          </div>
          <p className="text-xs text-text-tertiary">
            Need more credits during beta?{' '}
            <a href="mailto:support@zenvort.com" className="underline text-primary">
              Contact us
            </a>
          </p>
        </div>
      </div>
    </AppLayout>
  )
}
