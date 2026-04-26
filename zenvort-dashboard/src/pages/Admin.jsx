import AppLayout from '@/components/layout/AppLayout'

const MOCK_USERS = [
  { id: 'u1', email: 'alice@example.com', credits: 500, plan: 'Starter', joined: '2026-01-15' },
  { id: 'u2', email: 'bob@corp.io', credits: 1200, plan: 'Pro', joined: '2026-02-03' },
  { id: 'u3', email: 'charlie@gmail.com', credits: 0, plan: 'Enterprise', joined: '2026-03-20' },
]

export default function Admin() {
  return (
    <AppLayout>
      <div className="bg-white border border-border rounded-md overflow-hidden max-w-[700px]">
        <div className="px-4 py-3 bg-slate-50 border-b border-border">
          <h3 className="text-[13px] font-medium text-text-primary">Users</h3>
        </div>
        {/* Table header */}
        <div className="grid grid-cols-[1fr_1fr_1fr_80px_100px] px-4 py-2 bg-slate-50 border-b border-border">
          <span className="text-[10px] text-text-tertiary">EMAIL</span>
          <span className="text-[10px] text-text-tertiary">CREDITS</span>
          <span className="text-[10px] text-text-tertiary">PLAN</span>
          <span className="text-[10px] text-text-tertiary">JOINED</span>
          <span className="text-[10px] text-text-tertiary">ACTION</span>
        </div>
        {MOCK_USERS.map((user, i) => (
          <div
            key={user.id}
            className={`grid grid-cols-[1fr_1fr_1fr_80px_100px] px-4 py-2.5 items-center ${
              i < MOCK_USERS.length - 1 ? 'border-b border-border' : ''
            }`}
          >
            <span className="text-[11px] text-text-secondary">{user.email}</span>
            <span className="text-[11px] text-text-secondary font-medium text-secondary">{user.credits}</span>
            <span className="text-[11px] text-text-secondary">{user.plan}</span>
            <span className="text-[11px] text-text-tertiary">{user.joined}</span>
            <span className="text-[11px] text-primary cursor-pointer hover:underline">Edit</span>
          </div>
        ))}
      </div>
    </AppLayout>
  )
}