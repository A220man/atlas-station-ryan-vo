import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

// Hoisted mock for axios
const { mockAxiosInstance, mockGet, mockPost } = vi.hoisted(() => {
  const mockGet = vi.fn()
  const mockPost = vi.fn()
  return {
    mockAxiosInstance: {
      get: mockGet,
      post: mockPost,
      interceptors: { response: { use: vi.fn() } },
      defaults: { headers: {} },
    },
    mockGet,
    mockPost,
  }
})

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

// Import App after mock is set up
import App from './App'

// Test wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGet.mockReset()
    mockPost.mockReset()
  })

  it('renders header with app name', async () => {
    mockGet
      .mockResolvedValueOnce({ data: { status: 'healthy', version: '1.0.0', database: 'connected' } })
      .mockResolvedValueOnce({ data: { jobs: [], total: 0, page: 1, page_size: 20 } })

    render(<App />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Atlas Station')).toBeInTheDocument()
    })
  })

  it('shows upload area', async () => {
    mockGet
      .mockResolvedValueOnce({ data: { status: 'healthy', version: '1.0.0', database: 'connected' } })
      .mockResolvedValueOnce({ data: { jobs: [], total: 0, page: 1, page_size: 20 } })

    render(<App />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Upload Videos')).toBeInTheDocument()
      // Text is split across elements, use partial match
      expect(screen.getByText(/click.*browse/i)).toBeInTheDocument()
    })
  })

  it('shows empty job list', async () => {
    mockGet
      .mockResolvedValueOnce({ data: { status: 'healthy', version: '1.0.0', database: 'connected' } })
      .mockResolvedValueOnce({ data: { jobs: [], total: 0, page: 1, page_size: 20 } })

    render(<App />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('No jobs yet. Upload a video to get started.')).toBeInTheDocument()
    })
  })

  it('displays job list with data', async () => {
    const mockJobs = [{
      id: 'test-job-1',
      type: 'restoration',
      status: 'completed',
      progress: 1.0,
      current_step: 'completed',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      files: [{
        id: 'file-1',
        job_id: 'test-job-1',
        original_filename: 'test.mp4',
        original_path: '/tmp/test.mp4',
        file_size: 1000000,
        duration: 10,
        width: 1920,
        height: 1080,
        fps: 30,
        codec: 'h264',
        has_audio: true,
        status: 'completed',
        progress: 1.0,
        error_message: null,
        output_path: '/tmp/output.mp4',
        output_size: 2000000,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        processed_at: new Date().toISOString(),
      }],
    }]

    mockGet
      .mockResolvedValueOnce({ data: { status: 'healthy', version: '1.0.0', database: 'connected' } })
      .mockResolvedValueOnce({ data: { jobs: mockJobs, total: 1, page: 1, page_size: 20 } })

    render(<App />, { wrapper: createWrapper() })

    await waitFor(() => {
      // Job ID is truncated to 8 chars + '...' in UI
      expect(screen.getByText('test-job...')).toBeInTheDocument()
      expect(screen.getByText('restoration')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
    })
  })
})