import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Callback from '../pages/Callback'

// Track navigation calls
const mockNavigate = vi.fn()

// Mock react-router-dom navigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock useAuth from @common-auth/react
const mockHandleCallback = vi.fn()
vi.mock('@common-auth/react', () => ({
  useAuth: () => ({
    handleCallback: mockHandleCallback,
  }),
}))

function renderCallback() {
  return render(
    <MemoryRouter initialEntries={['/callback?code=test&state=test']}>
      <Callback />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Callback', () => {
  it('navigates to returnTo when handleCallback returns state with returnTo', async () => {
    mockHandleCallback.mockResolvedValue({ returnTo: '/me/security' })

    renderCallback()

    await waitFor(() => {
      expect(mockHandleCallback).toHaveBeenCalledOnce()
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/me/security', { replace: true })
    })
  })

  it('navigates to /dashboard when handleCallback returns no state', async () => {
    mockHandleCallback.mockResolvedValue(undefined)

    renderCallback()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('navigates to /dashboard when handleCallback returns empty state', async () => {
    mockHandleCallback.mockResolvedValue({})

    renderCallback()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('shows error message when handleCallback fails', async () => {
    mockHandleCallback.mockRejectedValue(new Error('No matching state found'))

    renderCallback()

    await waitFor(() => {
      expect(screen.getByText('No matching state found')).toBeInTheDocument()
    })

    // Should show back button
    expect(screen.getByText('Back to Home')).toBeInTheDocument()
  })

  it('shows generic error for non-Error exceptions', async () => {
    mockHandleCallback.mockRejectedValue('unknown error')

    renderCallback()

    await waitFor(() => {
      expect(screen.getByText('Authentication failed')).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    // Never resolves, so stays in loading state
    mockHandleCallback.mockReturnValue(new Promise(() => {}))

    renderCallback()

    expect(screen.getByText('Processing authentication...')).toBeInTheDocument()
  })

  it('calls handleCallback only once (StrictMode protection)', async () => {
    mockHandleCallback.mockResolvedValue(undefined)

    renderCallback()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled()
    })

    // Should only be called once even with useRef guard
    expect(mockHandleCallback).toHaveBeenCalledTimes(1)
  })
})
