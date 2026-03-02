const REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'common-auth'
const BASE = `/keycloak-admin/realms/${REALM}`

export interface KcUser {
  id: string
  username: string
  email: string
  firstName?: string
  lastName?: string
  enabled: boolean
  emailVerified: boolean
  attributes?: Record<string, string[]>
  realmRoles?: string[]
}

export interface KcGroup {
  id: string
  name: string
  path: string
}

export interface CreateUserInput {
  email: string
  firstName: string
  lastName: string
  password: string
  temporary: boolean
  tenantId: string
}

export interface UpdateUserInput {
  firstName?: string
  lastName?: string
  email?: string
  enabled?: boolean
}

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
    throw new Error(`Keycloak Admin API error ${res.status}: ${text}`)
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }
  return res.json()
}

export async function findTenantGroup(
  token: string,
  tenantId: string,
): Promise<KcGroup | null> {
  const groups = await request<KcGroup[]>(
    `/groups?search=${encodeURIComponent(tenantId)}&exact=true`,
    token,
  )
  const find = (list: (KcGroup & { subGroups?: KcGroup[] })[]): KcGroup | null => {
    for (const g of list) {
      if (g.name === tenantId) return g
      if (g.subGroups) {
        const found = find(g.subGroups)
        if (found) return found
      }
    }
    return null
  }
  return find(groups as (KcGroup & { subGroups?: KcGroup[] })[])
}

export async function listGroupMembers(
  token: string,
  groupId: string,
): Promise<KcUser[]> {
  return request<KcUser[]>(`/groups/${groupId}/members?max=200`, token)
}

export async function listAllUsers(token: string): Promise<KcUser[]> {
  return request<KcUser[]>('/users?max=200', token)
}

export async function getUser(token: string, userId: string): Promise<KcUser> {
  return request<KcUser>(`/users/${userId}`, token)
}

export async function getUserRoles(
  token: string,
  userId: string,
): Promise<{ name: string }[]> {
  return request<{ name: string }[]>(
    `/users/${userId}/role-mappings/realm`,
    token,
  )
}

export async function createUser(
  token: string,
  input: CreateUserInput,
): Promise<string> {
  const res = await fetch(`${BASE}/users`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      username: input.email,
      email: input.email,
      firstName: input.firstName,
      lastName: input.lastName,
      enabled: true,
      emailVerified: true,
      attributes: { tenant_id: [input.tenantId] },
      credentials: [
        {
          type: 'password',
          value: input.password,
          temporary: input.temporary,
        },
      ],
    }),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`ユーザー作成失敗 (${res.status}): ${text}`)
  }
  const location = res.headers.get('Location') ?? ''
  return location.split('/').pop() ?? ''
}

export async function addUserToGroup(
  token: string,
  userId: string,
  groupId: string,
): Promise<void> {
  await request<void>(`/users/${userId}/groups/${groupId}`, token, {
    method: 'PUT',
  })
}

export async function assignRealmRole(
  token: string,
  userId: string,
  roleName: string,
): Promise<void> {
  const roles = await request<{ id: string; name: string }[]>('/roles', token)
  const role = roles.find((r) => r.name === roleName)
  if (!role) return
  await request<void>(`/users/${userId}/role-mappings/realm`, token, {
    method: 'POST',
    body: JSON.stringify([role]),
  })
}

export async function updateUser(
  token: string,
  userId: string,
  input: UpdateUserInput,
): Promise<void> {
  await request<void>(`/users/${userId}`, token, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
}

export async function setUserEnabled(
  token: string,
  userId: string,
  enabled: boolean,
): Promise<void> {
  await request<void>(`/users/${userId}`, token, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  })
}

export async function resetUserPassword(
  token: string,
  userId: string,
  newPassword: string,
  temporary = true,
): Promise<void> {
  await request<void>(`/users/${userId}/reset-password`, token, {
    method: 'PUT',
    body: JSON.stringify({
      type: 'password',
      value: newPassword,
      temporary,
    }),
  })
}
