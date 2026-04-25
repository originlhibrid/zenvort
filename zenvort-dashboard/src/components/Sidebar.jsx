import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Store } from '../store';

export function Sidebar({ onClose }) {
  const location = useLocation();
  const user = Store.getUser();
  const isAdmin = user && user.role === 'admin';

  const nav = [
    { path: '/dashboard', icon: '📊', label: 'Dashboard' },
    { path: '/keys', icon: '🔑', label: 'API Key' },
    { path: '/billing', icon: '💳', label: 'Billing' },
  ];
  if (isAdmin) nav.push({ path: '/admin', icon: '⚙️', label: 'Admin' });

  const handleLogout = () => {
    Store.clearAuth();
    window.location.href = '/';
  };

  return (
    <aside className="w-64 bg-slate-900 min-h-screen p-6 flex flex-col text-white flex-shrink-0">
      {onClose && (
        <button onClick={onClose} className="absolute top-4 right-4 text-white/60 hover:text-white md:hidden">✕</button>
      )}
      <Link to="/dashboard" className="text-xl font-bold mb-10">Zenvort</Link>
      <nav className="flex-1 space-y-1">
        {nav.map(item => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm font-medium ${
              location.pathname === item.path ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-white/10 hover:text-white'
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="pt-6 border-t border-white/10">
        <div className="px-4 py-2 text-sm text-slate-400 truncate mb-3">{user?.email || ''}</div>
        <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-2.5 w-full rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors text-sm">
          <span>🚪</span>
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}