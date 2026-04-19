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

// ── Group types ───────────────────────────────────────────────────────────────

export interface Group {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface GroupListResponse {
  items: Group[]
  total: number
  page: number
  page_size: number
}

export interface CreateGroupInput {
  name: string
  description?: string
}

export interface UpdateGroupInput {
  name?: string
  description?: string
  is_active?: boolean
}

export interface GroupMember {
  user_id: string
  email: string
  display_name: string | null
  added_at: string
}

export interface GroupMembersResponse {
  group_id: string
  members: GroupMember[]
  total: number
}

// ── Group operations ──────────────────────────────────────────────────────────

export async function listGroups(
  token: string,
  page = 1,
  pageSize = 20,
  search?: string,
): Promise<GroupListResponse> {
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (search) qs.set('search', search)
  return request<GroupListResponse>(`/groups?${qs}`, token)
}

export async function createGroup(
  token: string,
  input: CreateGroupInput,
): Promise<Group> {
  return request<Group>('/groups', token, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function updateGroup(
  token: string,
  groupId: string,
  input: UpdateGroupInput,
): Promise<Group> {
  return request<Group>(`/groups/${groupId}`, token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function deleteGroup(token: string, groupId: string): Promise<void> {
  return request<void>(`/groups/${groupId}`, token, { method: 'DELETE' })
}

export async function listGroupMembers(
  token: string,
  groupId: string,
): Promise<GroupMembersResponse> {
  return request<GroupMembersResponse>(`/groups/${groupId}/members`, token)
}

export async function addGroupMembers(
  token: string,
  groupId: string,
  userIds: string[],
): Promise<void> {
  return request<void>(`/groups/${groupId}/members`, token, {
    method: 'POST',
    body: JSON.stringify({ user_ids: userIds }),
  })
}

export async function removeGroupMember(
  token: string,
  groupId: string,
  userId: string,
): Promise<void> {
  return request<void>(`/groups/${groupId}/members/${userId}`, token, { method: 'DELETE' })
}

// ── Audit log types ───────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  tenant_id: string
  actor_id: string | null
  actor_email: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown>
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export interface AuditLogsResponse {
  logs: AuditLog[]
  total: number
  page: number
  per_page: number
}

// ── Audit log operations ──────────────────────────────────────────────────────

export async function listAuditLogs(
  token: string,
  params?: {
    tenant_id?: string
    action?: string
    actor_id?: string
    from_dt?: string
    to_dt?: string
    page?: number
    per_page?: number
  },
): Promise<AuditLogsResponse> {
  const qs = new URLSearchParams()
  if (params?.tenant_id) qs.set('tenant_id', params.tenant_id)
  if (params?.action) qs.set('action', params.action)
  if (params?.actor_id) qs.set('actor_id', params.actor_id)
  if (params?.from_dt) qs.set('from_dt', params.from_dt)
  if (params?.to_dt) qs.set('to_dt', params.to_dt)
  if (params?.page) qs.set('page', String(params.page))
  if (params?.per_page) qs.set('per_page', String(params.per_page))
  const q = qs.toString()
  return request<AuditLogsResponse>(`/audit/logs${q ? '?' + q : ''}`, token)
}

// ── Password policy types ─────────────────────────────────────────────────────

export interface PasswordPolicy {
  min_length: number
  require_uppercase: boolean
  require_digits: boolean
  require_special: boolean
  password_history: number
  expire_days: number
}

// ── Password policy operations ────────────────────────────────────────────────

export async function getPasswordPolicy(token: string): Promise<PasswordPolicy> {
  return request<PasswordPolicy>('/security/password-policy', token)
}

export async function getPasswordPolicyForTenant(
  token: string,
  tenantId?: string,
): Promise<PasswordPolicy> {
  const qs = new URLSearchParams()
  if (tenantId) qs.set('tenant_id', tenantId)
  return request<PasswordPolicy>(`/security/password-policy${qs.toString() ? `?${qs.toString()}` : ''}`, token)
}

export async function updatePasswordPolicy(
  token: string,
  input: PasswordPolicy,
): Promise<PasswordPolicy> {
  return request<PasswordPolicy>('/security/password-policy', token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function updatePasswordPolicyForTenant(
  token: string,
  input: PasswordPolicy,
  tenantId?: string,
): Promise<PasswordPolicy> {
  const qs = new URLSearchParams()
  if (tenantId) qs.set('tenant_id', tenantId)
  return request<PasswordPolicy>(`/security/password-policy${qs.toString() ? `?${qs.toString()}` : ''}`, token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

// ── Session settings types ────────────────────────────────────────────────────

export interface SessionSettings {
  access_token_lifespan: number
  sso_session_idle_timeout: number
  sso_session_max_lifespan: number
}

// ── Session settings operations ───────────────────────────────────────────────

export async function getSessionSettings(token: string): Promise<SessionSettings> {
  return request<SessionSettings>('/security/session', token)
}

export async function getSessionSettingsForTenant(
  token: string,
  tenantId?: string,
): Promise<SessionSettings> {
  const qs = new URLSearchParams()
  if (tenantId) qs.set('tenant_id', tenantId)
  return request<SessionSettings>(`/security/session${qs.toString() ? `?${qs.toString()}` : ''}`, token)
}

export async function updateSessionSettings(
  token: string,
  input: SessionSettings,
): Promise<SessionSettings> {
  return request<SessionSettings>('/security/session', token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function updateSessionSettingsForTenant(
  token: string,
  input: SessionSettings,
  tenantId?: string,
): Promise<SessionSettings> {
  const qs = new URLSearchParams()
  if (tenantId) qs.set('tenant_id', tenantId)
  return request<SessionSettings>(`/security/session${qs.toString() ? `?${qs.toString()}` : ''}`, token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}
