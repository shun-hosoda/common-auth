/**
 * Backend Admin API client.
 *
 * All requests go to /api/admin/... which Vite proxies to the FastAPI backend
 * (localhost:8000). The backend uses client_credentials to communicate with
 * the Keycloak Admin REST API — the user's JWT is only used for authz checks.
 */

const BASE = '/api/admin'

// ── Shared types ─────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  username: string
  email: string
  firstName?: string
  lastName?: string
  enabled: boolean
  emailVerified: boolean
  attributes?: Record<string, string[]>
}

export interface AdminClient {
  id: string
  clientId: string
  name?: string
  enabled: boolean
}

export interface CreateUserInput {
  email: string
  firstName?: string
  lastName?: string
  password: string
  temporary?: boolean
}

export interface UpdateUserInput {
  firstName?: string
  lastName?: string
  email?: string
  enabled?: boolean
}

export interface CreateClientInput {
  clientId: string
  name?: string
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  token: string,
  options?: RequestInit,
  baseOverride?: string,
): Promise<T> {
  const base = baseOverride ?? BASE
  const res = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Admin API error ${res.status}: ${text}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }
  return res.json() as Promise<T>
}

// ── User operations ───────────────────────────────────────────────────────────

export async function listUsers(token: string): Promise<AdminUser[]> {
  return request<AdminUser[]>('/users', token)
}

export async function getUser(token: string, userId: string): Promise<AdminUser> {
  return request<AdminUser>(`/users/${userId}`, token)
}

export async function createUser(
  token: string,
  input: CreateUserInput,
): Promise<{ id: string }> {
  return request<{ id: string }>('/users', token, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function updateUser(
  token: string,
  userId: string,
  input: UpdateUserInput,
): Promise<void> {
  return request<void>(`/users/${userId}`, token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

/** Soft-delete: disables the user via DELETE /admin/users/{id} */
export async function disableUser(token: string, userId: string): Promise<void> {
  return request<void>(`/users/${userId}`, token, { method: 'DELETE' })
}

export async function resetPassword(
  token: string,
  userId: string,
  newPassword: string,
  temporary = true,
): Promise<void> {
  return request<void>(`/users/${userId}/reset-password`, token, {
    method: 'POST',
    body: JSON.stringify({ newPassword, temporary }),
  })
}

export async function resetMfa(token: string, userId: string): Promise<void> {
  return request<void>(`/users/${userId}/reset-mfa`, token, { method: 'POST' })
}

// ── Client (tenant) operations ────────────────────────────────────────────────

export async function listClients(token: string): Promise<AdminClient[]> {
  return request<AdminClient[]>('/clients', token)
}

export async function createClient(
  token: string,
  input: CreateClientInput,
): Promise<{ id: string }> {
  return request<{ id: string }>('/clients', token, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

// ── MFA types ─────────────────────────────────────────────────────────────────

export interface MfaSettings {
  mfa_enabled: boolean
  mfa_method: string
}

export interface MfaUpdateResult {
  status: string
  mfa_enabled: boolean
  mfa_method: string
  users_updated: number
  users_failed: number
}

export interface MfaStatus {
  mfa_enabled: boolean
  mfa_method: string
  mfa_configured: boolean
}

// ── MFA operations (admin) ────────────────────────────────────────────────────

export async function getMfaSettings(token: string): Promise<MfaSettings> {
  return request<MfaSettings>('/security/mfa', token)
}

export async function updateMfaSettings(
  token: string,
  body: { mfa_enabled: boolean; mfa_method: string },
): Promise<MfaUpdateResult> {
  return request<MfaUpdateResult>('/security/mfa', token, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

// ── MFA status (auth router — uses baseOverride) ──────────────────────────────

export async function getMfaStatus(token: string): Promise<MfaStatus> {
  return request<MfaStatus>('/mfa-status', token, undefined, '/auth')
}

// ── Enriched users (app DB — includes group memberships) ──────────────────────

export interface EnrichedUser {
  id: string
  email: string
  displayName: string | null
  roles: string[]
  enabled: boolean
  jobTitle: string | null
  lastLoginAt: string | null
  createdAt: string | null
  tenantId: string
  groups: string[]
}

export async function listUsersWithGroups(token: string): Promise<EnrichedUser[]> {
  return request<EnrichedUser[]>('/users-with-groups', token)
}

// ── Invitation types ──────────────────────────────────────────────────────────

export interface InvitationResponse {
  id: string
  tenant_id: string
  email: string
  role: 'user' | 'tenant_admin'
  group_id: string | null
  invited_by: string | null
  custom_message: string | null
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  effective_status: 'pending' | 'accepted' | 'expired' | 'revoked'
  expires_at: string
  accepted_at: string | null
  revoked_at: string | null
  revoked_by: string | null
  created_at: string
}

export interface InvitationCreateItem {
  email: string
  role?: 'user' | 'tenant_admin'
  group_id?: string
}

export interface InvitationBulkRequest {
  invitations: InvitationCreateItem[]
  /** S-5 fix: custom_message is a bulk-level field, not per-recipient */
  custom_message?: string
}

export interface InvitationFailedItem {
  email: string
  reason: string
}

export interface InvitationBulkResponse {
  succeeded: InvitationResponse[]
  failed: InvitationFailedItem[]
}

export interface InvitationValidateResponse {
  valid: boolean
  email: string
  role: string
  tenant_display_name: string
  inviter_display_name: string | null
  custom_message: string | null
  mfa_required: boolean
  password_policy_hint: string | null
}

export interface InvitationAcceptRequest {
  token: string
  display_name: string
  password: string
}

export interface InvitationAcceptResponse {
  status: string
  mfa_required: boolean
  mfa_method: string | null
}

// ── Invitation operations (admin) ─────────────────────────────────────────────

export async function listInvitations(
  token: string,
  status?: string,
): Promise<InvitationResponse[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return request<InvitationResponse[]>(`/invitations${qs}`, token)
}

export async function createInvitations(
  token: string,
  body: InvitationBulkRequest,
): Promise<InvitationBulkResponse> {
  return request<InvitationBulkResponse>('/invitations', token, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function revokeInvitation(
  token: string,
  id: string,
): Promise<InvitationResponse> {
  return request<InvitationResponse>(`/invitations/${id}`, token, { method: 'DELETE' })
}

export async function resendInvitation(
  token: string,
  id: string,
): Promise<InvitationResponse> {
  return request<InvitationResponse>(`/invitations/${id}/resend`, token, { method: 'POST' })
}

// ── Invitation operations (public — no auth token) ────────────────────────────

const PUBLIC_BASE = '/api/invitations'

async function publicRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${PUBLIC_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Invitation API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function validateInvitationToken(
  token: string,
): Promise<InvitationValidateResponse> {
  return publicRequest<InvitationValidateResponse>(
    `/validate?token=${encodeURIComponent(token)}`,
  )
}

export async function acceptInvitation(
  body: InvitationAcceptRequest,
): Promise<InvitationAcceptResponse> {
  return publicRequest<InvitationAcceptResponse>('/accept', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
