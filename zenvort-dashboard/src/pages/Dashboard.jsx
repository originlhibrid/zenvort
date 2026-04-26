import AppLayout from '@/components/layout/AppLayout'
import { useAuth, useJobs } from '@/lib/store'
import { Badge } from '@/components/ui/badge'
import { useState } from 'react'

const MOCK_JOBS = [
  { id: 'abc12345', input: 'pdf', output: 'docx', status: 'DONE', createdAt: '2 min ago' },
  { id: 'def67890', input: 'mp4', output: 'mp3', status: 'PROCESSING', createdAt: '5 min ago' },
  { id: 'ghi11223', input: 'png', output: 'webp', status: 'PENDING', createdAt: '10 min ago' },
]

const statusVariant = {
  DONE: 'success',
  PROCESSING: 'processing',
  PENDING: 'pending',
}

const statusLabel = {
  DONE: 'DONE',
  PROCESSING: 'PROCESSING',
  PENDING: 'PENDING',
}

export default function Dashboard() {
  const { state } = useAuth()
  const { state: jobsState } = useJobs()
  const [dragging, setDragging] = useState(false)
  const jobs = MOCK_JOBS

  return (
    <AppLayout>
      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white border border-border rounded-md p-3">
          <div className="text-[10px] text-text-tertiary mb-1.5">Credits</div>
          <div className="text-[20px] font-medium text-secondary">{state.credits}</div>
        </div>
        <div className="bg-white border border-border rounded-md p-3">
          <div className="text-[10px] text-text-tertiary mb-1.5">Total jobs</div>
          <div className="text-[20px] font-medium text-primary">{jobs.length}</div>
        </div>
        <div className="bg-white border border-border rounded-md p-3">
          <div className="text-[10px] text-text-tertiary mb-1.5">Jobs today</div>
          <div className="text-[20px] font-medium text-accent">{jobs.length}</div>
        </div>
        <div className="bg-white border border-border rounded-md p-3">
          <div className="text-[10px] text-text-tertiary mb-1.5">Success rate</div>
          <div className="text-[20px] font-medium text-accent">100%</div>
        </div>
      </div>

      {/* Upload zone */}
      <div
        className={`bg-white border-2 border-dashed rounded-lg p-7 text-center cursor-pointer transition-colors ${
          dragging ? 'border-primary bg-indigo-50' : 'border-border'
        }`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false) }}
        onClick={() => {}}
      >
        <div className="w-8 h-8 bg-slate-100 rounded flex items-center justify-center mx-auto mb-2.5">
          <svg width="16" height="2" viewBox="0 0 16 2" fill="none" xmlns="http://www.w3.org/2000/svg" className="opacity-50">
            <rect width="16" height="2" rx="1" fill="#94a3b8"/>
          </svg>
        </div>
        <div className="text-[13px] text-text-secondary mb-1">Drop your file here or click to browse</div>
        <div className="text-[11px] text-text-tertiary">38 formats supported — video, audio, image, document</div>
      </div>

      {/* Jobs table */}
      <div className="bg-white border border-border rounded-md overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-[2fr_1fr_1fr_1fr_80px] px-3.5 py-2 bg-slate-50 border-b border-border">
          <span className="text-[10px] text-text-tertiary">JOB ID</span>
          <span className="text-[10px] text-text-tertiary">INPUT</span>
          <span className="text-[10px] text-text-tertiary">OUTPUT</span>
          <span className="text-[10px] text-text-tertiary">STATUS</span>
          <span className="text-[10px] text-text-tertiary">ACTION</span>
        </div>
        {/* Rows */}
        {jobs.map((job, i) => (
          <div
            key={job.id}
            className={`grid grid-cols-[2fr_1fr_1fr_1fr_80px] px-3.5 py-2.5 items-center ${
              i < jobs.length - 1 ? 'border-b border-border' : ''
            }`}
          >
            <span className="text-[11px] text-text-secondary font-mono">{job.id}</span>
            <span className="text-[11px] text-text-secondary">{job.input}</span>
            <span className="text-[11px] text-text-secondary">{job.output}</span>
            <span>
              <Badge variant={statusVariant[job.status]}>{statusLabel[job.status]}</Badge>
            </span>
            <span className={`text-[11px] ${job.status === 'DONE' ? 'text-primary cursor-pointer' : 'text-text-tertiary'}`}>
              {job.status === 'DONE' ? 'Download' : '—'}
            </span>
          </div>
        ))}
      </div>
    </AppLayout>
  )
}