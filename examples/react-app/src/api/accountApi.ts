/**
 * Password change API client.
 *
 * Routes requests through the FastAPI backend (/api/users/me/password),
 * which validates the current password via Keycloak ROPC grant and then
 * updates it via the Keycloak Admin REST API.
 *
 * Vite proxy: /api → http://127.0.0.1:8000
 *
 * Success : 204 No Content
 * Failure : 400 { message: string }  (wrong newPassword policy / etc.)
 * Auth err: 401 { message: string }  (wrong currentPassword or expired token)
 */

// ── Error type ────────────────────────────────────────────────────────────────

export class ChangePasswordError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ChangePasswordError'
  }
}

// ── API ───────────────────────────────────────────────────────────────────────

/**
 * Change the current user's password via the FastAPI backend.
 *
 * @param token           - The user's current access token (Bearer)
 * @param currentPassword - The user's current password (verified server-side)
 * @param newPassword     - The desired new password
 * @throws ChangePasswordError on HTTP 4xx/5xx
 */
export async function changePasswordApi(
  token: string,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  if (!token) {
    throw new ChangePasswordError(401, 'セッションが切れています。再ログインしてください。')
  }

  const res = await fetch('/api/users/me/password', {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ currentPassword, newPassword }),
  })

  // 204 = success
  if (res.status === 204) return

  // Parse error body
  let message = 'パスワード変更に失敗しました'
  if (res.status === 401) {
    message = '現在のパスワードが正しくありません'
  } else {
    try {
      const json = await res.json()
      if (typeof json.message === 'string' && json.message) {
        message = json.message
      }
    } catch {
      // ignore JSON parse failure
    }
  }

  throw new ChangePasswordError(res.status, message)
}
