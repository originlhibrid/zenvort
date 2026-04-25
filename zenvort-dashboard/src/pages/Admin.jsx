import React, { useState, useEffect } from 'react';
import { StatCard } from '../components/StatCard';
import { api } from '../api';
import { Store } from '../store';
import { useNavigate } from 'react-router-dom';

const formatDate = (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

export function Admin() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [adjustingUser, setAdjustingUser] = useState(null);
  const [adjustAmount, setAdjustAmount] = useState('');
  const [adjustError, setAdjustError] = useState('');

  useEffect(() => {
    if (!Store.isAuthenticated()) { navigate('/login'); return; }
    const user = Store.getUser();
    if (!user || user.role !== 'admin') { navigate('/dashboard'); return; }
    fetchData();
  }, []);

  const fetchData = () => {
    Promise.all([
      api.adminStats().then(d => { setStats(d); setLoadingStats(false); }).catch(() => setLoadingStats(false)),
      api.adminUsers(page).then(d => { setUsers(d.users || []); setTotal(d.total || 0); setLoadingUsers(false); }).catch(() => setLoadingUsers(false)),
    ]);
  };

  const handleAdjustCredits = async (userId) => {
    const amount = parseInt(adjustAmount);
    if (isNaN(amount)) { setAdjustError('Enter a number'); return; }
    setAdjustError('');
    try {
      await api.adminAdjustCredits(userId, amount);
      window.showToast('Credits adjusted!', 'success');
      setAdjustingUser(null);
      fetchData();
    } catch (err) {
      setAdjustError(err.message);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-1">Admin Panel</h1>
      <p className="text-slate-500 mb-8">Platform management and monitoring.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Total Users" value={loadingStats ? '...' : (stats?.totalUsers ?? 0)} icon="👥" />
        <StatCard title="Total Jobs" value={loadingStats ? '...' : (stats?.totalJobs ?? 0)} icon="📁" />
        <StatCard title="Jobs Today" value={loadingStats ? '...' : (stats?.jobsToday ?? 0)} icon="📅" />
        <StatCard title="Active Jobs" value={loadingStats ? '...' : (stats?.activeJobs ?? 0)} icon="⚡" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-900">Users</h2>
          <button onClick={fetchData} className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">↻ Refresh</button>
        </div>

        {loadingUsers ? (
          <div className="p-6 space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Credits</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Jobs</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Joined</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm font-medium text-slate-900">{u.email}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{u.credits}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{u._count ? u._count.jobs : 0}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full font-medium ${u.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-800'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">{formatDate(u.createdAt)}</td>
                    <td className="px-6 py-4">
                      {adjustingUser === u.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={adjustAmount}
                            onChange={e => setAdjustAmount(e.target.value)}
                            placeholder="Amount"
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                          <button onClick={() => handleAdjustCredits(u.id)} className="px-3 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 transition-colors">Apply</button>
                          <button onClick={() => setAdjustingUser(null)} className="px-3 py-1 border border-slate-200 text-xs rounded hover:bg-slate-50 transition-colors">Cancel</button>
                          {adjustError && <span className="text-red-600 text-xs">{adjustError}</span>}
                        </div>
                      ) : (
                        <button onClick={() => { setAdjustingUser(u.id); setAdjustAmount(''); setAdjustError(''); }} className="text-indigo-600 hover:text-indigo-700 text-sm font-medium">Adjust Credits</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-slate-200 flex justify-between items-center">
            <span className="text-sm text-slate-500">{total} total users · Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button onClick={() => { setPage(page - 1); fetchData(); }} disabled={page <= 1} className="px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50 transition-colors">← Previous</button>
              <button onClick={() => { setPage(page + 1); fetchData(); }} disabled={page >= totalPages} className="px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50 transition-colors">Next →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}