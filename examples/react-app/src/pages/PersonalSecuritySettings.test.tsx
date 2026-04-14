import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PersonalSecuritySettings from '../pages/PersonalSecuritySettings'

// --- Mock navigate ---
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// --- Mock @common-auth/react ---
const mockConfigureMFA = vi.fn()
const mockLogout = vi.fn()
const mockGetAccessToken = vi.fn().mockReturnValue('fake-token')
const mockHasRole = vi.fn().mockReturnValue(false)

vi.mock('@common-auth/react', () => ({
  useAuth: () => ({
    user: {
      profile: {
        sub: 'user-1',
        iss: 'http://localhost:8080',
        aud: 'example-app',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        email: 'user@example.com',
        name: 'Test User',
        preferred_username: 'testuser',
        tenant_id: 'acme-corp',
      },
      expired: false,
    },
    isAuthenticated: true,
    logout: mockLogout,
    hasRole: mockHasRole,
    getAccessToken: mockGetAccessToken,
    configureMFA: mockConfigureMFA,
  }),
}))

// --- Mock adminApi ---
const mockGetMfaStatus = vi.fn()
vi.mock('../api/adminApi', () => ({
  getMfaStatus: (...args: unknown[]) => mockGetMfaStatus(...args),
}))

// --- Mock layout components to simplify rendering ---
vi.mock('../components/layout', () => ({
  useIsMobile: () => false,
  UserDropdown: () => <div data-testid="user-dropdown" />,
  SideNav: () => <nav data-testid="side-nav" />,
  MobileDrawer: () => null,
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <PersonalSecuritySettings />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetAccessToken.mockReturnValue('fake-token')
  mockHasRole.mockReturnValue(false)
})

describe('PersonalSecuritySettings', () => {
  describe('MFA disabled at tenant level', () => {
    it('shows info message instead of button when MFA is disabled', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: false,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/MFAはテナント管理者によって有効化されていません/)).toBeInTheDocument()
      })

      // Should NOT show the configure button
      expect(screen.queryByText('MFAを設定する')).not.toBeInTheDocument()
      expect(screen.queryByText('MFAを再設定する')).not.toBeInTheDocument()
    })

    it('shows status label as "MFA 無効"', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: false,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/MFA 無効/)).toBeInTheDocument()
      })
    })
  })

  describe('MFA enabled, not yet configured', () => {
    it('shows "MFAを設定する" button', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('MFAを設定する')).toBeInTheDocument()
      })
    })

    it('shows status label as "MFA 未設定"', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/MFA 未設定/)).toBeInTheDocument()
      })
    })
  })

  describe('MFA enabled and configured', () => {
    it('shows "MFAを再設定する" button', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: true,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('MFAを再設定する')).toBeInTheDocument()
      })
    })

    it('shows status label as "MFA 設定済み"', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: true,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/MFA 設定済み/)).toBeInTheDocument()
      })
    })
  })

  describe('MFA button interaction', () => {
    it('calls configureMFA with returnTo=/me/security on click', async () => {
      mockConfigureMFA.mockResolvedValue(undefined)
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('MFAを設定する')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('MFAを設定する'))

      await waitFor(() => {
        expect(mockConfigureMFA).toHaveBeenCalledWith({ returnTo: '/me/security' })
      })
    })

    it('shows loading state while MFA configure is in progress', async () => {
      // Never resolves to keep loading state
      mockConfigureMFA.mockReturnValue(new Promise(() => {}))
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('MFAを設定する')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('MFAを設定する'))

      await waitFor(() => {
        expect(screen.getByText('遷移中...')).toBeInTheDocument()
      })
    })

    it('shows error when configureMFA fails', async () => {
      mockConfigureMFA.mockRejectedValue(new Error('Redirect failed'))
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: true,
        mfa_method: 'totp',
        mfa_configured: true,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('MFAを再設定する')).toBeInTheDocument()
      })

      fireEvent.click(screen.getByText('MFAを再設定する'))

      await waitFor(() => {
        expect(screen.getByText(/Redirect failed/)).toBeInTheDocument()
      })
    })
  })

  describe('loading state', () => {
    it('shows loading indicator while fetching MFA status', () => {
      mockGetMfaStatus.mockReturnValue(new Promise(() => {}))

      renderPage()

      expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    })
  })

  describe('error state', () => {
    it('shows error message when MFA status fetch fails', async () => {
      mockGetMfaStatus.mockRejectedValue(new Error('Network error'))

      renderPage()

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument()
      })
    })
  })

  describe('password section', () => {
    it('shows password change button', async () => {
      mockGetMfaStatus.mockResolvedValue({
        mfa_enabled: false,
        mfa_method: 'totp',
        mfa_configured: false,
      })

      renderPage()

      await waitFor(() => {
        expect(screen.getByText('パスワードを変更する')).toBeInTheDocument()
      })
    })
  })
})
