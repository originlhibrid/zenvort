import React, { useState, useEffect } from 'react';
import { StatCard } from '../components/StatCard';
import { JobTable } from '../components/JobTable';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';
import { Store } from '../store';

const formats = ['pdf', 'mp4', 'mp3', 'wav', 'docx', 'xlsx', 'pptx', 'txt', 'webm', 'avi', 'mov', 'mkv', 'flac', 'aac', 'html'];

export function Dashboard() {
  const navigate = useNavigate();
  const [usage, setUsage] = useState(null);
  const [loadingUsage, setLoadingUsage] = useState(true);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [file, setFile] = useState(null);
  const [outputFormat, setOutputFormat] = useState('pdf');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!Store.isAuthenticated()) { navigate('/login'); return; }
    fetchData();
  }, []);

  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'PENDING' || j.status === 'PROCESSING');
    if (hasActive) {
      const timer = setTimeout(fetchJobs, 5000);
      return () => clearTimeout(timer);
    }
  }, [jobs]);

  const fetchData = async () => {
    await Promise.all([fetchUsage(), fetchJobs()]);
  };

  const fetchUsage = async () => {
    try {
      const data = await api.getUsage();
      setUsage(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingUsage(false);
    }
  };

  const fetchJobs = async () => {
    try {
      const data = await api.listJobs(page);
      setJobs(data.jobs || []);
      setTotalPages(Math.ceil((data.total || 0) / 20));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      await api.createJob(file, outputFormat);
      window.showToast('Job created!', 'success');
      setFile(null);
      fetchJobs();
    } catch (err) {
      setError(err.message || 'Upload failed');
      window.showToast(err.message || 'Upload failed', 'error');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-1">Dashboard</h1>
      <p className="text-slate-500 mb-8">Convert files and track your jobs.</p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Credits" value={loadingUsage ? '...' : (usage?.credits ?? 0)} icon="💰" />
        <StatCard title="Total Jobs" value={loadingUsage ? '...' : (usage?.totalJobs ?? 0)} icon="📁" />
        <StatCard title="Jobs Today" value={loadingUsage ? '...' : (usage?.jobsToday ?? 0)} icon="📅" />
        <StatCard title="Success Rate" value={loadingUsage ? '...' : ((usage?.successRate ?? 0) + '%')} icon="✅" />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Upload File</h2>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">{error}</div>
        )}
        <form onSubmit={handleUpload} className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <input
              type="file"
              onChange={e => setFile(e.target.files[0])}
              className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-sm file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              required
            />
          </div>
          <div className="w-36">
            <select
              value={outputFormat}
              onChange={e => setOutputFormat(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm"
            >
              {formats.map(f => (
                <option key={f} value={f}>{f.toUpperCase()}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={uploading || !file}
            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium text-sm transition-colors"
          >
            {uploading ? 'Uploading...' : 'Convert'}
          </button>
        </form>
      </div>

      <h2 className="text-lg font-semibold text-slate-900 mb-4">Recent Jobs</h2>
      <JobTable
        jobs={jobs}
        loading={loadingJobs}
        totalPages={totalPages}
        page={page}
        onPageChange={(p) => { setPage(p); fetchJobs(); }}
      />
    </div>
  );
}