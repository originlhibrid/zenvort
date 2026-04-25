import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Store } from '../store';
import { useNavigate } from 'react-router-dom';

export function ApiKey() {
  const navigate = useNavigate();
  const [revealed, setRevealed] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookInput, setWebhookInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!Store.isAuthenticated()) { navigate('/login'); return; }
    api.getMe().then(user => {
      setWebhookUrl(user.webhookUrl || '');
      setWebhookInput(user.webhookUrl || '');
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const apiKey = Store.getApiKey() || '';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(apiKey);
    window.showToast('Copied!', 'success');
  };

  const saveWebhook = async () => {
    setSaving(true);
    try {
      await api.updateWebhook(webhookInput);
      setWebhookUrl(webhookInput);
      window.showToast('Webhook updated!', 'success');
    } catch (err) {
      window.showToast(err.message || 'Failed to update webhook', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-1">API Key</h1>
      <p className="text-slate-500 mb-8">Use this key to authenticate with the Zenvort API.</p>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <label className="block text-sm font-semibold text-slate-700 mb-3">Your API Key</label>
        <div className="flex gap-3">
          <input
            type={revealed ? 'text' : 'password'}
            value={revealed ? apiKey : apiKey.slice(0, 8) + '...' + apiKey.slice(-8)}
            readOnly
            className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-sm text-slate-700"
          />
          <button
            onClick={() => setRevealed(!revealed)}
            className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 rounded-lg font-medium text-sm text-slate-700 transition-colors"
          >
            {revealed ? 'Hide' : 'Reveal'}
          </button>
          <button
            onClick={copyToClipboard}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors"
          >
            Copy
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-3">Keep this key secret. Do not share it in public places.</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <label className="block text-sm font-semibold text-slate-700 mb-2">Webhook URL</label>
        <p className="text-sm text-slate-500 mb-4">Receive notifications when your jobs complete.</p>
        <div className="flex gap-3">
          <input
            type="url"
            value={webhookInput}
            onChange={e => setWebhookInput(e.target.value)}
            placeholder="https://your-server.com/webhook"
            className="flex-1 px-4 py-2.5 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
          />
          <button
            onClick={saveWebhook}
            disabled={saving || webhookInput === webhookUrl}
            className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 font-medium text-sm transition-colors"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
        {webhookUrl && (
          <p className="text-sm text-slate-400 mt-3">Current: <span className="font-mono">{webhookUrl}</span></p>
        )}
      </div>
    </div>
  );
}