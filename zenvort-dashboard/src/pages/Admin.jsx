import AppLayout from '@/components/layout/AppLayout'
import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/store'

export default function Admin() {
  const { state } = useAuth()
  const [users, setUsers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editAmount, setEditAmount] = useState('')
  const [error, setError] = useState('')

  const apiKey = localStorage.getItem('zenvort_api_key')
  const authHeader = { Authorization: `Bearer ${apiKey}` }

  const fetchUsers = () => {
    fetch('http://localhost:3000/admin/users?page=1', { headers: authHeader })
      .then(r => r.json())
      .then(data => { if (data.users) setUsers(data.users) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  const fetchStats = () => {
    fetch('http://localhost:3000/admin/stats', { headers: authHeader })
      .then(r => r.json())
      .then(data => setStats(data))
      .catch(() => {})
  }

  useEffect(() => {
    fetchUsers()
    fetchStats()
  }, [])

  const handleEdit = (user) => {
    setEditingId(user.id)
    setEditAmount('')
    setError('')
  }

  const handleSave = async (userId) => {
    const amount = parseInt(editAmount)
    if (isNaN(amount)) { setError('Enter a number'); return }
    setError('')
    try {
      const res = await fetch(`http://localhost:3000/admin/users/${userId}/credits`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeader },
        body: JSON.stringify({ amount }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Update failed')
      fetchUsers()
      setEditingId(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (dateStr) => {
    try { return new Date(dateStr).toLocaleDateString('en-IN') } catch { return dateStr }
  }

  return (
    <AppLayout>
      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Total users', value: stats.totalUsers },
            { label: 'Total jobs', value: stats.totalJobs },
            { label: 'Jobs today', value: stats.jobsToday },
            { label: 'Active jobs', value: stats.activeJobs },
          ].map(s => (
            <div key={s.label} className="bg-white border border-border rounded-md p-3 dark:bg-slate-900 dark:border-slate-700">
              <div className="text-[10px] text-text-tertiary mb-1">{s.label}</div>
              <div className="text-[20px] font-medium text-primary">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Users table */}
      <div className="bg-white border border-border rounded-md overflow-hidden max-w-[800px] dark:bg-slate-900 dark:border-slate-700">
        <div className="px-4 py-3 bg-slate-50 border-b border-border dark:bg-slate-800 dark:border-slate-700">
          <h3 className="text-[13px] font-medium text-text-primary">Users</h3>
        </div>
        {/* Table header */}
        <div className="grid grid-cols-[2fr_80px_80px_120px_80px] px-4 py-2 bg-slate-50 border-b border-border dark:bg-slate-800 dark:border-slate-700">
          <span className="text-[10px] text-text-tertiary">EMAIL</span>
          <span className="text-[10px] text-text-tertiary">CREDITS</span>
          <span className="text-[10px] text-text-tertiary">ROLE</span>
          <span className="text-[10px] text-text-tertiary">JOINED</span>
          <span className="text-[10px] text-text-tertiary">ACTION</span>
        </div>

        {loading && users.length === 0 ? (
          <div className="px-4 py-6 text-center text-[12px] text-text-tertiary">Loading...</div>
        ) : users.length === 0 ? (
          <div className="px-4 py-6 text-center text-[12px] text-text-tertiary">No users found.</div>
        ) : (
          users.map((user, i) => (
            <div
              key={user.id}
              className={`grid grid-cols-[2fr_80px_80px_120px_80px] px-4 py-2.5 items-center ${
                i < users.length - 1 ? 'border-b border-border dark:border-slate-700' : ''
              }`}
            >
              <span className="text-[11px] text-text-secondary">{user.email}</span>
              <span className="text-[11px] text-text-secondary font-medium text-secondary">{user.credits}</span>
              <span className="text-[11px] text-text-tertiary">{user.role}</span>
              <span className="text-[11px] text-text-tertiary">{formatDate(user.createdAt)}</span>
              <span>
                {editingId === user.id ? (
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      value={editAmount}
                      onChange={e => setEditAmount(e.target.value)}
                      placeholder="±amount"
                      className="w-16 border border-border rounded px-1.5 py-0.5 text-[11px] dark:bg-slate-800 dark:border-slate-700"
                    />
                    <button
                      onClick={() => handleSave(user.id)}
                      className="text-[11px] text-primary hover:underline"
                    >
                      Save
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => handleEdit(user)}
                    className="text-[11px] text-primary cursor-pointer hover:underline"
                  >
                    Edit
                  </button>
                )}
              </span>
            </div>
          ))
        )}

        {error && <div className="px-4 py-2 text-[11px] text-red-500">{error}</div>}
      </div>
    </AppLayout>
  )
}