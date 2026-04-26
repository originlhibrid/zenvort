import AppLayout from '@/components/layout/AppLayout'
import { useAuth } from '@/lib/store'

const plans = [
  { name: 'Starter', price: '₹199', credits: '500', current: false },
  { name: 'Pro', price: '₹599', credits: '2,000', current: true },
  { name: 'Enterprise', price: '₹1,999', credits: '10,000', current: false },
]

export default function Billing() {
  const { state } = useAuth()

  return (
    <AppLayout>
      <div className="space-y-4 max-w-[600px]">
        {/* Current plan */}
        <div className="bg-white border border-border rounded-md p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-3">Current Plan</h3>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[15px] font-medium text-primary">Pro</div>
              <div className="text-[11px] text-text-tertiary">₹599/mo · 2,000 credits</div>
            </div>
            <div className="text-[11px] bg-accent/20 text-accent px-2.5 py-0.5 rounded-full font-medium">
              Active
            </div>
          </div>
        </div>

        {/* Credits balance */}
        <div className="bg-white border border-border rounded-md p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-3">Credits Balance</h3>
          <div className="text-[24px] font-medium text-secondary">{state.credits}</div>
          <p className="text-[11px] text-text-tertiary mt-1">credits remaining</p>
        </div>

        {/* Available plans */}
        <div className="bg-white border border-border rounded-md p-5">
          <h3 className="text-[13px] font-medium text-text-primary mb-3">Available Plans</h3>
          <div className="flex gap-3">
            {plans.map(plan => (
              <div key={plan.name} className="flex-1 border border-border rounded-[10px] p-4">
                <div className="text-[13px] font-medium text-text-primary">{plan.name}</div>
                <div className="text-[18px] font-medium text-text-primary mt-1">{plan.price}</div>
                <div className="text-[11px] text-text-tertiary mt-0.5">{plan.credits} credits</div>
                {plan.current ? (
                  <div className="mt-3 text-[11px] text-primary font-medium">Current plan</div>
                ) : (
                  <div className="mt-3 text-[11px] border border-border text-text-secondary rounded-[6px] py-1.5 text-center cursor-pointer hover:bg-slate-50 transition-colors">
                    Upgrade
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}