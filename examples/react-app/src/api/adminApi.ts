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
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
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
