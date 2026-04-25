import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Store } from '../store';
import { useNavigate } from 'react-router-dom';

const formatDate = (d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

export function Billing() {
  const navigate = useNavigate();
  const [credits, setCredits] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loadingTx, setLoadingTx] = useState(true);

  useEffect(() => {
    if (!Store.isAuthenticated()) { navigate('/login'); return; }
    api.getUsage().then(d => setCredits(d.credits)).catch(console.error);
    api.getTransactions().then(d => { setTransactions(d.logs || []); setLoadingTx(false); }).catch(() => setLoadingTx(false));
  }, []);

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-1">Billing</h1>
      <p className="text-slate-500 mb-8">Manage your credits and view transaction history.</p>

      <div className="bg-white rounded-xl border border-slate-200 p-8 mb-8">
        <p className="text-sm font-medium text-slate-500 mb-2">Credit Balance</p>
        <p className="text-5xl font-bold text-slate-900">{credits ?? '...'}</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Transaction History</h2>
        </div>
        {loadingTx ? (
          <div className="p-12 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-4xl mb-4">📋</div>
            <p className="text-slate-500">No transactions yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[500px]">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Reason</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Job ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {transactions.map(tx => (
                  <tr key={tx.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 text-sm text-slate-600">{formatDate(tx.createdAt)}</td>
                    <td className="px-6 py-4 text-sm text-slate-600 capitalize">{tx.reason}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-900">{tx.amount > 0 ? '+' : ''}{tx.amount}</td>
                    <td className="px-6 py-4 text-sm font-mono text-slate-400">{tx.jobId ? tx.jobId.slice(0, 8) + '...' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}