import React, { useState, useEffect } from 'react';

export function Toast() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    window.showToast = (message, type = 'info') => {
      const id = Date.now();
      setToasts(prev => [...prev, { id, message, type }]);
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 4000);
    };
  }, []);

  const colors = {
    success: 'bg-emerald-500',
    error: 'bg-red-500',
    info: 'bg-indigo-600'
  };
  const icons = { success: '✓', error: '✕', info: 'ℹ' };

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm space-y-3">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-center gap-3 px-5 py-4 rounded-xl shadow-lg text-white animate-slide-in ${colors[t.type]}`}>
          <span className="font-bold">{icons[t.type]}</span>
          <span className="flex-1 text-sm">{t.message}</span>
          <button onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))} className="text-white/70 hover:text-white text-xl leading-none ml-2">×</button>
        </div>
      ))}
    </div>
  );
}