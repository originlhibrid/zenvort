import AppLayout from '@/components/layout/AppLayout'
import { useAuth } from '@/lib/store'

export default function ApiKey() {
  const { state } = useAuth()

  const copyKey = () => {
    if (state.apiKey) {
      navigator.clipboard.writeText(state.apiKey)
    }
  }

  return (
    <AppLayout>
      <div className="bg-white border border-border rounded-md p-5 max-w-[500px]">
        <h3 className="text-[13px] font-medium text-text-primary mb-1">Your API Key</h3>
        <p className="text-[11px] text-text-tertiary mb-4">
          Use this key to authenticate your requests to the Zenvort API.
        </p>
        <div className="flex items-center gap-2">
          <code className="flex-1 bg-slate-50 border border-border rounded px-3 py-2 text-[12px] font-mono text-text-secondary break-all dark:bg-slate-800 dark:border-slate-700">
            {state.apiKey || 'No API key generated yet'}
          </code>
          <button
            onClick={copyKey}
            className="bg-primary text-white text-[12px] px-3 py-2 rounded-[6px] font-medium cursor-pointer hover:bg-primary/90 transition-colors whitespace-nowrap"
          >
            Copy
          </button>
        </div>
      </div>
    </AppLayout>
  )
}