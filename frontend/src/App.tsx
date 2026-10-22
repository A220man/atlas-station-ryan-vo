import { Upload, FileText, RefreshCw, Pause, Play, X, Settings, Loader2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import clsx from 'clsx'

// Types
interface VideoFile {
  id: string
  job_id: string
  original_filename: string
  original_path: string
  file_size: number
  duration: number | null
  width: number | null
  height: number | null
  fps: number | null
  codec: string | null
  has_audio: boolean
  status: string
  progress: number
  error_message: string | null
  output_path: string | null
  output_size: number | null
  created_at: string
  updated_at: string
  processed_at: string | null
}

interface Job {
  id: string
  type: string
  status: string
  progress: number
  current_step: string | null
  error_message: string | null
  input_dir: string | null
  output_dir: string | null
  options: Record<string, any> | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
  files: VideoFile[]
}

interface JobListResponse {
  jobs: Job[]
  total: number
  page: number
  page_size: number
}

interface UploadResponse {
  job_id: string
  files: VideoFile[]
}

interface HealthResponse {
  status: string
  version: string
  database: string
}

// API client
const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle auth error
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

const STATUS_COLORS: Record<string, string> = {
  pending: 'badge-pending',
  queued: 'badge-queued',
  processing: 'badge-processing',
  completed: 'badge-completed',
  failed: 'badge-failed',
  paused: 'badge-paused',
  cancelled: 'badge-cancelled',
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const StatusBadge = ({ status }: { status: string }) => (
  <span className={clsx(STATUS_COLORS[status] || 'badge-pending')}>
    {status.charAt(0).toUpperCase() + status.slice(1)}
  </span>
)

const ProgressBar = ({ progress }: { progress: number }) => (
  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
    <div
      className="h-full bg-blue-600 transition-all duration-300 ease-out"
      style={{ width: `${Math.min(100, Math.max(0, progress * 100))}%` }}
    />
  </div>
)

const FileUpload = () => {
  const [files, setFiles] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post<UploadResponse>('/jobs/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setFiles([])
    },
  })

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    setFiles((prev) => [...prev, ...droppedFiles])
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    setFiles((prev) => [...prev, ...selectedFiles])
  }

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (files.length === 0) return

    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    formData.append('job_type', 'restoration')
    formData.append('options', JSON.stringify({ deblock: true, denoise: true, crf: 23 }))

    uploadMutation.mutate(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="card p-6">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-slate-900 mb-2">Upload Videos</h2>
        <p className="text-slate-500 text-sm">
          Drag and drop video files or click to browse. Supports MP4, MOV, MKV, AVI.
        </p>
      </div>

      <div
        className={clsx(
          'border-2 border-dashed rounded-xl p-8 text-center transition-colors',
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-blue-400'
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          multiple
          accept="video/*"
          onChange={handleFileSelect}
          className="hidden"
          id="file-input"
          disabled={uploadMutation.isPending}
        />
        <label htmlFor="file-input" className="cursor-pointer">
          <Upload className="mx-auto h-12 w-12 text-slate-400 mb-4" />
          <p className="text-slate-600 mb-1">
            {dragActive ? 'Drop files here...' : 'Click or drag videos to upload'}
          </p>
          <p className="text-slate-400 text-sm">Multiple files supported</p>
        </label>
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-2 max-h-60 overflow-y-auto scrollbar-thin">
          {files.map((file, index) => (
            <div key={index} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <FileText className="h-5 w-5 text-slate-400" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{file.name}</p>
                <p className="text-xs text-slate-500">{formatBytes(file.size)}</p>
              </div>
              <button
                type="button"
                onClick={() => removeFile(index)}
                className="text-slate-400 hover:text-red-500 transition-colors"
                disabled={uploadMutation.isPending}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex gap-3">
        <button
          type="submit"
          className="btn-primary flex-1"
          disabled={files.length === 0 || uploadMutation.isPending}
        >
          {uploadMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Upload {files.length} file{files.length !== 1 ? 's' : ''}
            </>
          )}
        </button>
      </div>

      {uploadMutation.isError && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          Upload failed: {uploadMutation.error?.message}
        </div>
      )}
    </form>
  )
}

const JobRow = ({ job }: { job: Job }) => {
  const queryClient = useQueryClient()

  const pauseMutation = useMutation({
    mutationFn: () => api.post(`/jobs/${job.id}/pause`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const resumeMutation = useMutation({
    mutationFn: () => api.post(`/jobs/${job.id}/resume`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const cancelMutation = useMutation({
    mutationFn: () => api.post(`/jobs/${job.id}/cancel`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const canPause = ['processing', 'queued'].includes(job.status)
  const canResume = job.status === 'paused'
  const canCancel = ['pending', 'queued', 'processing', 'paused'].includes(job.status)

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="px-4 py-3">
        <div className="font-mono text-sm text-slate-600">{job.id.slice(0, 8)}...</div>
      </td>
      <td className="px-4 py-3">
        <div className="font-medium text-slate-900">{job.type}</div>
        <div className="text-xs text-slate-500">{job.files.length} file(s)</div>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={job.status} />
      </td>
      <td className="px-4 py-3">
        <div className="w-32">
          <ProgressBar progress={job.progress} />
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-slate-500">
        {job.current_step || '-'}
      </td>
      <td className="px-4 py-3 text-sm text-slate-500">
        {new Date(job.created_at).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {canPause && (
            <button
              onClick={() => pauseMutation.mutate()}
              disabled={pauseMutation.isPending}
              className="btn-ghost p-2"
              title="Pause"
            >
              <Pause className="h-4 w-4" />
            </button>
          )}
          {canResume && (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="btn-ghost p-2"
              title="Resume"
            >
              <Play className="h-4 w-4" />
            </button>
          )}
          {canCancel && (
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="btn-ghost p-2 text-red-600 hover:bg-red-50"
              title="Cancel"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

const JobList = () => {
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['jobs', page],
    queryFn: async () => {
      const response = await api.get<JobListResponse>(`/jobs?page=${page}&page_size=${pageSize}`)
      return response.data
    },
    refetchInterval: 3000,
  })

  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Processing Jobs</h2>
        </div>
        <div className="p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400 mx-auto mb-2" />
          <p className="text-slate-500">Loading jobs...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Processing Jobs</h2>
        </div>
        <div className="p-8 text-center text-red-600">
          <AlertCircle className="h-8 w-8 mx-auto mb-2" />
          <p>Failed to load jobs</p>
        </div>
      </div>
    )
  }

  const jobs = data?.jobs || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="card overflow-hidden">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Processing Jobs</h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">{total} job(s)</span>
          <button
            onClick={() => refetch()}
            className="btn-ghost p-2"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Progress</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Current Step</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Created</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                  <FileText className="h-12 w-12 mx-auto text-slate-300 mb-3" />
                  <p>No jobs yet. Upload a video to get started.</p>
                </td>
              </tr>
            ) : (
              jobs.map((job) => <JobRow key={job.id} job={job} />)
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="p-4 border-t border-slate-200 flex items-center justify-between">
          <div className="text-sm text-slate-500">
            Page {page} of {totalPages}
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost p-2"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-ghost p-2"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const Header = () => {
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get<HealthResponse>('/health')
      return response.data
    },
  })

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Settings className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-xl font-bold text-slate-900">Atlas Station</h1>
            <span className="text-xs text-slate-400">v{health?.version || '1.0.0'}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', health?.database === 'connected' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
              {health?.database === 'connected' ? '● Database Connected' : '● Database Disconnected'}
            </span>
          </div>
        </div>
      </div>
    </header>
  )
}

const App = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <FileUpload />
          </div>
          <div className="lg:col-span-2">
            <JobList />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App