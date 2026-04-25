import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

const features = [
  { icon: '🎬', title: 'Video & Audio', subtitle: 'FFmpeg', desc: 'Convert mp4, mov, avi, mp3, wav, aac and more' },
  { icon: '📄', title: 'Documents', subtitle: 'LibreOffice', desc: 'Convert pdf, docx, pptx, xlsx, odt and more' },
  { icon: '⚡', title: 'Async Queue', subtitle: 'BullMQ', desc: 'Jobs processed reliably with automatic retries' },
  { icon: '☁️', title: 'Cloud Storage', subtitle: 'R2', desc: 'Files stored securely on Cloudflare R2' },
  { icon: '🔔', title: 'Webhooks', subtitle: '', desc: 'Get notified instantly when your conversion completes' },
  { icon: '💰', title: 'Credit Based', subtitle: '', desc: 'Pay only for what you use, starting at 1 credit per job' },
];

const plans = [
  { name: 'Starter', credits: 500, price: 'Rs.199', features: ['500 credits', 'All formats', 'Webhooks', 'API access'] },
  { name: 'Pro', credits: 2000, price: 'Rs.599', featured: true, features: ['2000 credits', 'All formats', 'Webhooks', 'API access', 'Priority support'] },
  { name: 'Enterprise', credits: 10000, price: 'Rs.1999', features: ['10000 credits', 'All formats', 'Webhooks', 'API access', 'Dedicated support'] },
];

export function Landing() {
  const [plansData, setPlansData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getPlans().then(d => { setPlansData(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <span className="font-bold text-xl text-slate-900">Zenvort</span>
          <div className="flex items-center gap-3">
            <Link to="/login" className="px-4 py-2 text-slate-600 hover:text-slate-900 font-medium">Login</Link>
            <Link to="/signup" className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition-colors">Get Started</Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-white py-28 text-center">
        <div className="max-w-3xl mx-auto px-6">
          <span className="inline-block bg-indigo-50 text-indigo-700 rounded-full px-4 py-1.5 text-sm font-medium mb-6">
            File Conversion API — Now in Beta
          </span>
          <h1 className="text-5xl font-bold text-slate-900 leading-tight">
            Convert any file.<br />Instantly at scale.
          </h1>
          <p className="text-xl text-slate-500 mt-6 max-w-2xl mx-auto">
            Transform files between 50+ formats with our powerful REST API. Video, audio, documents — all in one line of code.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link to="/signup" className="px-8 py-3.5 bg-indigo-600 text-white text-lg rounded-xl hover:bg-indigo-700 font-medium shadow-sm transition-colors">
              Get Started Free
            </Link>
            <a href="#docs" className="px-8 py-3.5 border-2 border-slate-200 text-slate-700 text-lg rounded-xl hover:bg-slate-50 font-medium transition-colors">
              View Docs
            </a>
          </div>
          <p className="text-sm text-slate-400 mt-5">100 free credits on signup. No payment required.</p>
        </div>
      </section>

      {/* How it works */}
      <section className="bg-slate-50 py-24" id="docs">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-slate-900 text-center mb-4">How it works</h2>
          <p className="text-slate-500 text-center mb-14">Three steps to convert any file.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                n: '1',
                title: 'Upload & Convert',
                code: `curl -X POST https://api.zenvort.com/jobs \\
  -H "Authorization: Bearer YOUR_KEY" \\
  -F "file=@video.mp4" \\
  -F "outputFormat=mp3"`
              },
              {
                n: '2',
                title: 'Poll Status',
                code: `curl https://api.zenvort.com/jobs/{jobId} \\
  -H "Authorization: Bearer YOUR_KEY"

// {"status": "DONE", "outputUrl": "..."}`
              },
              {
                n: '3',
                title: 'Download Result',
                code: `curl -o output.mp3 \\
  "https://r2.zenvort.com/outputs/.../output.mp3"`
              },
            ].map((step, i) => (
              <div key={i} className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
                <div className="bg-indigo-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">{step.n}</div>
                <h3 className="font-semibold text-slate-900 mt-4 mb-3">{step.title}</h3>
                <pre className="bg-slate-900 text-green-400 rounded-lg p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap">{step.code}</pre>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-white py-24">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-slate-900 text-center mb-4">Everything you need</h2>
          <p className="text-slate-500 text-center mb-14">Built for developers, by developers.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div key={i} className="border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow">
                <div className="text-2xl mb-3">{f.icon}</div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-slate-900">{f.title}</h3>
                  {f.subtitle && <span className="text-xs text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">{f.subtitle}</span>}
                </div>
                <p className="text-sm text-slate-500">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-slate-50 py-24">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-slate-900 text-center mb-4">Simple, credit-based pricing</h2>
          <p className="text-slate-500 text-center mb-14">Buy credits, use them whenever. No subscriptions.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {(loading ? plans : plansData.map((p, i) => ({ ...p, _i: i }))).map((plan, i) => (
              <div key={i} className={`bg-white rounded-2xl p-8 border ${plan.featured || plan._i === 1 ? 'border-indigo-600 border-2 relative' : 'border-slate-200'}`}>
                {(plan.featured || plan._i === 1) && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-600 text-white px-4 py-1 rounded-full text-xs font-medium">Most Popular</span>
                )}
                <h3 className="font-bold text-lg text-slate-900">{plan.name || plan.pack}</h3>
                <div className="flex items-baseline gap-1 mt-4 mb-6">
                  <span className="text-3xl font-bold text-indigo-600">{plan.credits}</span>
                  <span className="text-slate-500">credits</span>
                </div>
                <div className="text-2xl font-bold text-slate-900 mb-6">{plan.amount || plan.price}</div>
                <ul className="space-y-2 mb-8">
                  {(plan.features || [`${plan.credits} credits`, 'All formats', 'Webhooks', 'API access']).map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-slate-600">
                      <span className="text-green-500">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <Link to="/signup" className={`block text-center py-2.5 rounded-lg font-medium transition-colors ${plan.featured || plan._i === 1 ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'border border-slate-300 text-slate-700 hover:bg-slate-50'}`}>
                  Get Started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-white py-14">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-start gap-8">
          <div>
            <h2 className="font-bold text-xl mb-2">Zenvort</h2>
            <p className="text-slate-400 text-sm">Convert any file. Instantly at scale.</p>
          </div>
          <div className="flex gap-8 text-sm">
            <a href="#" className="text-slate-300 hover:text-white transition-colors">Docs</a>
            <a href="#" className="text-slate-300 hover:text-white transition-colors">GitHub</a>
            <a href="#" className="text-slate-300 hover:text-white transition-colors">Status</a>
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-6 mt-10 pt-8 border-t border-slate-800 text-slate-400 text-sm">
          © 2024 Zenvort. All rights reserved.
        </div>
      </footer>
    </div>
  );
}