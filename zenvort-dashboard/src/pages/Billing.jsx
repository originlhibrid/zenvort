import { BASE_URL } from '../lib/api.js';
import AppLayout from '@/components/layout/AppLayout'
import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/store'

const PLAN_LABELS = {
  starter: 'Starter',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

export default function Billing() {
  const { state } = useAuth()
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)

  const apiKey = localStorage.getItem('zenvort_api_key')
  const authHeader = { Authorization: `Bearer ${apiKey}` }

  useEffect(() => {
    fetch(BASE_URL + '/billing/plans')
      .then(r => r.json())
      .then(data => { if (Array.isArray(data)) setPlans(data) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <AppLayout>
      <div className="space-y-4 max-w-[600px]">
        {/* Credits balance */}
        <div className="bg-white border border-border rounded-md p-5 dark:bg-slate-900 dark:border-slate-700">
          <h3 className="text-[13px] font-medium text-text-primary mb-3">Credits Balance</h3>
          <div className="text-[24px] font-medium text-secondary">{state.credits}</div>
          <p className="text-[11px] text-text-tertiary mt-1">credits remaining</p>
        </div>

        {/* Available plans */}
        <div className="bg-white border border-border rounded-md p-5 dark:bg-slate-900 dark:border-slate-700">
          <h3 className="text-[13px] font-medium text-text-primary mb-3">Credit Packs</h3>
          {loading ? (
            <div className="text-[12px] text-text-tertiary">Loading plans...</div>
          ) : plans.length === 0 ? (
            <div className="text-[12px] text-text-tertiary">No plans available</div>
          ) : (
            <div className="flex gap-3">
              {plans.map(plan => (
                <div key={plan.pack} className="flex-1 border border-border rounded-[10px] p-4">
                  <div className="text-[13px] font-medium text-text-primary">{plan.name}</div>
                  <div className="text-[18px] font-medium text-text-primary mt-1">₹{plan.amount}</div>
                  <div className="text-[11px] text-text-tertiary mt-0.5">{plan.credits} credits</div>
                  <div className="mt-3 text-[11px] border border-border text-text-secondary rounded-[6px] py-1.5 text-center cursor-pointer hover:bg-slate-50 transition-colors dark:hover:bg-slate-800">
                    Buy now
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}