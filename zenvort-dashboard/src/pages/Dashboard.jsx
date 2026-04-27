import { BASE_URL } from '../lib/api.js';
import AppLayout from '@/components/layout/AppLayout'
import { Badge } from '@/components/ui/badge'
import { useState, useEffect, useRef } from 'react'

const statusVariant = {
  DONE: 'success',
  PROCESSING: 'processing',
  PENDING: 'pending',
  FAILED: 'destructive',
}

const statusLabel = {
  DONE: 'DONE',
  PROCESSING: 'PROCESSING',
  PENDING: 'PENDING',
  FAILED: 'FAILED',
}

// Generated from worker/routes.py ROUTES dict — always in sync with backend
const FORMAT_COMPATIBILITY = {
  avi:  { category: 'video',     to: ['flac', 'gif', 'mov', 'mp3', 'mp4', 'ogg', 'wav', 'webm'] },
  avif: { category: 'image',    to: ['bmp', 'gif', 'jpg', 'pdf', 'png', 'tiff', 'txt', 'webp'] },
  bmp:  { category: 'image',    to: ['avif', 'gif', 'jpg', 'png', 'tiff', 'txt', 'webp'] },
  csv:  { category: 'document', to: ['docx', 'html', 'pdf', 'txt'] },
  docx: { category: 'document', to: ['epub', 'html', 'pdf', 'rtf', 'txt'] },
  epub: { category: 'document', to: ['docx', 'html', 'pdf', 'txt'] },
  flac: { category: 'audio',    to: ['mp3', 'mp4', 'ogg', 'wav'] },
  gif:  { category: 'image',    to: ['avif', 'bmp', 'jpg', 'pdf', 'png', 'tiff', 'txt', 'webp'] },
  html: { category: 'document', to: ['docx', 'pdf', 'txt'] },
  jpg:  { category: 'image',    to: ['avif', 'bmp', 'gif', 'pdf', 'png', 'tiff', 'txt', 'webp'] },
  md:   { category: 'document', to: ['docx', 'epub', 'html', 'pdf', 'rtf', 'txt'] },
  mov:  { category: 'video',    to: ['avi', 'flac', 'gif', 'mp3', 'mp4', 'ogg', 'wav', 'webm'] },
  mp3:  { category: 'audio',    to: ['flac', 'mp4', 'ogg', 'wav'] },
  mp4:  { category: 'video',    to: ['avi', 'flac', 'gif', 'mov', 'mp3', 'ogg', 'webm'] },
  odp:  { category: 'document', to: ['pdf'] },
  ods:  { category: 'document', to: ['html', 'pdf', 'txt'] },
  odt:  { category: 'document', to: ['docx', 'html', 'pdf', 'txt'] },
  ogg:  { category: 'audio',    to: ['flac', 'mp3', 'mp4', 'wav'] },
  pdf:  { category: 'document', to: ['docx', 'epub', 'html', 'jpg', 'png', 'rtf', 'txt'] },
  png:  { category: 'image',    to: ['avif', 'bmp', 'gif', 'jpg', 'pdf', 'tiff', 'txt', 'webp'] },
  pptx: { category: 'document', to: ['docx', 'html', 'pdf', 'txt'] },
  rtf:  { category: 'document', to: ['docx', 'html', 'pdf', 'txt'] },
  tiff: { category: 'image',    to: ['avif', 'bmp', 'gif', 'jpg', 'png', 'txt', 'webp'] },
  txt:  { category: 'document', to: ['docx', 'epub', 'html', 'pdf'] },
  wav:  { category: 'audio',    to: ['flac', 'mp3', 'mp4', 'ogg'] },
  webm: { category: 'video',    to: ['avi', 'flac', 'mov', 'mp3', 'mp4', 'ogg', 'wav'] },
  webp: { category: 'image',    to: ['avif', 'bmp', 'gif', 'jpg', 'pdf', 'png', 'tiff', 'txt'] },
  xlsx: { category: 'document', to: ['csv', 'docx', 'html', 'pdf', 'txt'] },
}

// In sync with FORMAT_COMPATIBILITY supported formats
const FORMAT_LABELS = {
  avi: 'AVI', avif: 'AVIF', bmp: 'BMP', csv: 'CSV', docx: 'DOCX',
  epub: 'EPUB', flac: 'FLAC', gif: 'GIF', html: 'HTML',
  jpg: 'JPG', md: 'MD', mov: 'MOV', mp3: 'MP3', mp4: 'MP4',
  odp: 'ODP', ods: 'ODS', odt: 'ODT', ogg: 'OGG',
  pdf: 'PDF', png: 'PNG', pptx: 'PPTX', rtf: 'RTF',
  tiff: 'TIFF', txt: 'TXT', wav: 'WAV', webm: 'WebM',
  webp: 'WebP', xlsx: 'XLSX',
}

function Toast({ message, type, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])
  const colors = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  }
  return (
    <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-lg border text-[13px] shadow-lg animate-in slide-in-from-bottom-2 ${colors[type] || colors.info}`}>
      {message}
    </div>
  )
}

export default function Dashboard() {
  const [jobs, setJobs] = useState([])
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState(null)
  const [detectedFormat, setDetectedFormat] = useState(null)
  const [availableFormats, setAvailableFormats] = useState([])
  const [outputFormat, setOutputFormat] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState(null)
  const fileInputRef = useRef(null)

  const apiKey = localStorage.getItem('zenvort_api_key')
  const authHeader = { Authorization: `Bearer ${apiKey}` }

  const showToast = (message, type = 'info') => setToast({ message, type })

  // Fetch jobs from API
  const fetchJobs = async () => {
    try {
      const res = await fetch(BASE_URL + '/jobs?page=1&limit=20', { headers: authHeader })
      const data = await res.json()
      if (res.ok) setJobs(data.jobs || [])
    } catch {
      // silently fail — keep existing jobs
    }
  }

  // Fetch usage stats
  const fetchUsage = async () => {
    try {
      const res = await fetch(BASE_URL + '/billing/usage', { headers: authHeader })
      const data = await res.json()
      if (res.ok) setUsage(data)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }

  // Refresh credits from /user/me
  const refreshCredits = async () => {
    try {
      const res = await fetch(BASE_URL + '/user/me', { headers: authHeader })
      const data = await res.json()
      if (res.ok) {
        localStorage.setItem('zenvort_user', JSON.stringify(data))
        window.dispatchEvent(new Event('credits-updated'))
      }
    } catch {}
  }

  useEffect(() => {
    fetchJobs()
    fetchUsage()
  }, [])

  // Poll for job updates — only when there are in-flight jobs
  useEffect(() => {
    const hasPending = jobs.some(j => j.status === 'PENDING' || j.status === 'PROCESSING')
    if (!hasPending) return
    const interval = setInterval(async () => {
      await fetchJobs()
    }, 5000)
    return () => clearInterval(interval)
  }, [jobs])

  // Listen for external credit refresh events
  useEffect(() => {
    const handler = () => fetchUsage()
    window.addEventListener('credits-updated', handler)
    return () => window.removeEventListener('credits-updated', handler)
  }, [])

  // Submit job
  const handleSubmit = async () => {
    if (!file) {
      showToast('Please select a file first', 'error')
      return
    }
    if (!outputFormat) {
      showToast('Please select an output format', 'error')
      return
    }
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('outputFormat', outputFormat)
      const res = await fetch(BASE_URL + '/jobs', {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}` },
        body: form,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Submission failed')
      showToast(`Job queued — ID: ${data.jobId.slice(0, 8)}`, 'success')
      setFile(null)
      setDetectedFormat(null)
      setAvailableFormats([])
      setOutputFormat('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await fetchJobs()
    } catch (err) {
      showToast(err.message, 'error')
    } finally {
      setSubmitting(false)
    }
  }

  // Detect format and show compatible output formats
  const handleFileSelect = (selectedFile) => {
    if (!selectedFile) return

    const MAX_SIZE = 100 * 1024 * 1024
    if (selectedFile.size > MAX_SIZE) {
      showToast('File too large. Maximum size is 100MB.', 'error')
      return
    }

    const ext = selectedFile.name.split('.').pop().toLowerCase()

    setFile(selectedFile)
    setOutputFormat('')

    if (FORMAT_COMPATIBILITY[ext]) {
      setDetectedFormat(ext)
      setAvailableFormats(FORMAT_COMPATIBILITY[ext].to)
    } else {
      setDetectedFormat(null)
      setAvailableFormats([])
      showToast(`Format .${ext} not recognized. Try a different file.`, 'error')
    }
  }

  // Drag handlers
  const handleDragOver = (e) => {
    e.preventDefault()
    setDragging(true)
  }
  const handleDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false)
  }
  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) handleFileSelect(dropped)
  }
  const handleFileChange = (e) => {
    if (e.target.files?.[0]) handleFileSelect(e.target.files[0])
  }

  const clearFile = (e) => {
    e.stopPropagation()
    setFile(null)
    setDetectedFormat(null)
    setAvailableFormats([])
    setOutputFormat('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function formatTimeLeft(expiresAt) {
    if (!expiresAt) return null
    const diff = new Date(expiresAt) - new Date()
    if (diff <= 0) return 'expired'
    const mins = Math.floor(diff / 60000)
    const secs = Math.floor((diff % 60000) / 1000)
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }

  const stats = [
    {
      label: "Credits Remaining",
      value: usage?.credits ?? 0,
      sub: "100 free on signup",
      icon: "⚡",
      color: "text-yellow-400",
    },
    {
      label: "Total Conversions",
      value: usage?.totalJobs ?? 0,
      sub: `${usage?.jobsToday ?? 0} today`,
      icon: "🔄",
      color: "text-blue-400",
    },
    {
      label: "Success Rate",
      value: `${usage?.successRate ?? 0}%`,
      sub: "all time",
      icon: "✅",
      color: "text-green-400",
    },
    {
      label: "Formats Supported",
      value: "28",
      sub: "input formats",
      icon: "📄",
      color: "text-purple-400",
    },
  ]

  const maxCount = Math.max(...(usage?.dailyUsage?.map(d => d.count) ?? [1]), 1)

  return (
    <AppLayout>
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        {stats.map(stat => (
          <div key={stat.label} className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <span>{stat.icon}</span>
              <span className="text-xs text-muted-foreground">{stat.label}</span>
            </div>
            <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{stat.sub}</div>
          </div>
        ))}
      </div>

      {/* Credit warning */}
      {(usage?.credits ?? 0) < 10 && usage && (
        <div className="mb-4 rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-3 text-sm text-orange-400">
          ⚠️ You have {usage.credits} credits remaining.
          <a href="/billing" className="underline ml-1">View plans →</a>
        </div>
      )}

      {/* Daily usage chart */}
      {usage?.dailyUsage?.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4 mb-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">
            Conversions — last 30 days
          </h3>
          <div className="flex items-end gap-1 h-24">
            {usage.dailyUsage.map(day => (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-primary/60 rounded-sm"
                  style={{
                    height: `${maxCount > 0 ? (day.count / maxCount) * 96 : 0}px`,
                    minHeight: day.count > 0 ? '4px' : '0',
                  }}
                  title={`${day.date}: ${day.count} conversions`}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload zone */}
      <div
        className={`bg-white border-2 border-dashed rounded-lg p-7 text-center cursor-pointer transition-colors ${
          dragging ? 'border-primary bg-indigo-50 dark:bg-indigo-900/20' : 'border-border'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
        />
        {file ? (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-indigo-600 dark:text-indigo-400 uppercase">
                {detectedFormat || '?'}
              </span>
            </div>
            <div className="text-left min-w-0">
              <p className="text-sm font-medium text-slate-900 dark:text-white truncate max-w-xs">
                {file.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={clearFile}
              className="ml-auto text-slate-400 hover:text-red-500 transition-colors text-lg leading-none"
              aria-label="Remove file"
            >
              ×
            </button>
          </div>
        ) : (
          <>
            <div className="w-8 h-8 bg-slate-100 rounded flex items-center justify-center mx-auto mb-2.5">
              <svg width="16" height="2" viewBox="0 0 16 2" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-50">
                <rect width="16" height="2" rx="1" fill="#94a3b8"/>
              </svg>
            </div>
            <div className="text-[13px] text-text-secondary mb-1">Drop your file here or click to browse</div>
            <div className="text-[11px] text-text-tertiary">Video, audio, image, document — up to 100 MB</div>
          </>
        )}
      </div>

      {/* Output format selector */}
      <div className="bg-white border border-border rounded-md p-5 dark:bg-slate-900 dark:border-slate-700">
        {detectedFormat ? (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm text-slate-500 dark:text-slate-400">Detected:</span>
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-700 uppercase tracking-wide">
                .{detectedFormat}
              </span>
              <span className="text-sm text-slate-400 dark:text-slate-500">
                — {FORMAT_COMPATIBILITY[detectedFormat].category}
              </span>
            </div>

            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Convert to:
            </p>

            <div className="flex flex-wrap gap-2">
              {availableFormats.map(fmt => (
                <button
                  key={fmt}
                  onClick={() => setOutputFormat(fmt)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-150 ${
                    outputFormat === fmt
                      ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                      : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-600 hover:border-indigo-400 dark:hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400'
                  }`}
                >
                  .{fmt}
                  <span className="ml-1 text-xs opacity-60 uppercase">{FORMAT_LABELS[fmt]}</span>
                </button>
              ))}
            </div>

            {outputFormat && (
              <div className="mt-3 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                <span>✓</span>
                <span>Converting .{detectedFormat} → .{outputFormat}</span>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400 dark:text-slate-500 italic">
            Upload a file to see available conversion formats
          </p>
        )}

        {/* Submit button */}
        <div className="mt-4">
          <button
            onClick={handleSubmit}
            disabled={!file || !outputFormat || submitting}
            className={`w-full py-3 rounded-lg font-medium transition-all ${
              !file || !outputFormat || submitting
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer'
            }`}
          >
            {submitting
              ? 'Converting...'
              : outputFormat
                ? `Convert to .${outputFormat}`
                : 'Select output format'}
          </button>
        </div>
      </div>

      {/* Jobs table */}
      <div className="bg-white border border-border rounded-md overflow-hidden dark:bg-slate-900 dark:border-slate-700">
        {/* Table header */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_80px] px-3.5 py-2 bg-slate-50 border-b border-border dark:bg-slate-800 dark:border-slate-700">
          <span className="text-[10px] text-text-tertiary">JOB ID</span>
          <span className="text-[10px] text-text-tertiary">INPUT</span>
          <span className="text-[10px] text-text-tertiary">OUTPUT</span>
          <span className="text-[10px] text-text-tertiary">STATUS</span>
          <span className="text-[10px] text-text-tertiary">ACTION</span>
        </div>

        {loading && jobs.length === 0 ? (
          <div className="px-3.5 py-6 text-center text-[12px] text-text-tertiary">Loading jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="px-3.5 py-6 text-center text-[12px] text-text-tertiary">No jobs yet — upload a file above to get started.</div>
        ) : (
          jobs.map((job, i) => (
            <div
              key={job.id}
              className={`grid grid-cols-[2fr_1fr_1fr_1fr_80px] px-3.5 py-2.5 items-center ${
                i < jobs.length - 1 ? 'border-b border-border dark:border-slate-700' : ''
              }`}
            >
              <span className="text-[11px] text-text-secondary font-mono">{job.id.slice(0, 12)}...</span>
              <span className="text-[11px] text-text-secondary">{job.inputFormat?.toUpperCase()}</span>
              <span className="text-[11px] text-text-secondary">{job.outputFormat?.toUpperCase()}</span>
              <span>
                <Badge variant={statusVariant[job.status] || 'outline'}>
                  {statusLabel[job.status] || job.status}
                </Badge>
              </span>
              <span className="text-[11px]">
                {job.status === 'DONE' && job.outputUrl ? (
                  <div className="flex flex-col gap-0.5">
                    <a
                      href={job.outputUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary cursor-pointer hover:underline"
                      onClick={() => refreshCredits()}
                    >
                      Download
                    </a>
                    {job.expiresAt && (
                      <span className="text-[10px] text-orange-400">
                        ⏱ {formatTimeLeft(job.expiresAt)}
                      </span>
                    )}
                  </div>
                ) : job.status === 'FAILED' ? (
                  <span className="text-red-500 text-[10px]" title={job.error}>Error</span>
                ) : (
                  <span className="text-text-tertiary">—</span>
                )}
              </span>
              {job.status === 'FAILED' && job.error && (
                <div className="col-span-5 px-3.5 pb-2 text-[10px] text-red-500">{job.error}</div>
              )}
            </div>
          ))
        )}
      </div>
    </AppLayout>
  )
}