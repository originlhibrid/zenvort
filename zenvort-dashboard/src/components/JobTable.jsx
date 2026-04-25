import React from 'react';

const statusColors = {
  PENDING: 'bg-amber-100 text-amber-800',
  PROCESSING: 'bg-blue-100 text-blue-800',
  DONE: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800'
};

export function JobTable({ jobs, loading, totalPages, page, onPageChange }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-6 space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <div className="text-4xl mb-4">📭</div>
        <p className="text-slate-600 font-medium">No jobs yet.</p>
        <p className="text-slate-400 text-sm mt-2">Upload a file above to get started.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[650px]">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">ID</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Input</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Output</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Created</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {jobs.map(job => (
              <tr key={job.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-6 py-4 text-sm font-mono text-slate-600">{job.id.slice(0, 8)}...</td>
                <td className="px-6 py-4 text-sm text-slate-600 font-medium">{(job.inputFormat || '').toUpperCase()}</td>
                <td className="px-6 py-4 text-sm text-slate-600 font-medium">{(job.outputFormat || '').toUpperCase()}</td>
                <td className="px-6 py-4">
                  <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${statusColors[job.status] || 'bg-slate-100 text-slate-700'}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-slate-500">{new Date(job.createdAt).toLocaleDateString()}</td>
                <td className="px-6 py-4">
                  {job.status === 'DONE' && job.outputUrl ? (
                    <a href={job.outputUrl} target="_blank" rel="noreferrer" className="text-indigo-600 hover:text-indigo-700 text-sm font-medium transition-colors">Download</a>
                  ) : <span className="text-slate-300">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-slate-200 flex justify-between items-center">
          <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button onClick={() => onPageChange(page - 1)} disabled={page <= 1} className="px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-40 transition-colors">← Previous</button>
            <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages} className="px-4 py-2 border border-slate-200 rounded-lg text-sm hover:bg-slate-50 disabled:opacity-40 transition-colors">Next →</button>
          </div>
        </div>
      )}
    </div>
  );
}