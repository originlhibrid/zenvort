import React from 'react';
import { Store } from '../store';

export function Navbar({ onMenuOpen }) {
  const user = Store.getUser();
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center flex-shrink-0">
      <button onClick={onMenuOpen} className="md:hidden text-slate-600 text-xl">☰</button>
      <div className="hidden md:block text-sm text-slate-500">{user?.email}</div>
      <div className="flex items-center gap-4">
        <span className="text-sm font-medium text-slate-600">{user?.credits ?? 0} credits</span>
      </div>
    </header>
  );
}