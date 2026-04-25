import React from 'react';

export function StatCard({ title, value, icon }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
        </div>
        <div className="text-2xl opacity-80">{icon}</div>
      </div>
    </div>
  );
}