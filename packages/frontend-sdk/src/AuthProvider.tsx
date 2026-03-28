import { useCallback, useEffect, useMemo, useState } from "react";
import { UserManager, User } from "oidc-client-ts";
import { AuthContext } from "./AuthContext";
import type { AuthProviderProps } from "./types";

function extractRealmRoles(user: User): string[] {
  // Access token を優先（Keycloak は realm_access を access token に付与するが ID token には付与しない場合がある）
  const accessToken = user.access_token;
  if (accessToken) {
    try {
      const parts = accessToken.split(".");
      if (parts.length === 3) {
        const payload = parts[1];
        const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
        const decoded: unknown = JSON.parse(atob(padded));
        if (decoded && typeof decoded === "object") {
          const ra = (decoded as Record<string, unknown>).realm_access;
          if (ra && typeof ra === "object") {
            const roles = (ra as Record<string, unknown>).roles;
            if (Array.isArray(roles)) return roles as string[];
          }
        }
      }
    } catch {
      // fall through to ID token profile
    }
  }
  // フォールバック: ID token の profile から試みる
  const profile = user.profile;
  if (!profile || typeof profile !== "object") return [];
  const realmAccess = (profile as Record<string, unknown>).realm_access;
  if (!realmAccess || typeof realmAccess !== "object") return [];
  const roles = (realmAccess as Record<string, unknown>).roles;
  return Array.isArray(roles) ? (roles as string[]) : [];
}

export function AuthProvider({
  authority,
  clientId,
  redirectUri,
  postLogoutRedirectUri,
  scope = "openid profile email",
  automaticSilentRenew = true,
  children,
}: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const userManager = useMemo(
    () =>
      new UserManager({
        authority,
        client_id: clientId,
        redirect_uri: redirectUri,
        post_logout_redirect_uri: postLogoutRedirectUri || redirectUri,
        response_type: "code",
        scope,
        automaticSilentRenew,
      }),
    [authority, clientId, redirectUri, postLogoutRedirectUri, scope, automaticSilentRenew]
  );

  useEffect(() => {
    const loadUser = async () => {
      try {
        const currentUser = await userManager.getUser();
        setUser(currentUser);
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Failed to load user"));
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();

    const handleUserLoaded = (loadedUser: User) => {
      setUser(loadedUser);
      setError(null);
    };

    const handleUserUnloaded = () => {
      setUser(null);
    };

    const handleSilentRenewError = (err: Error) => {
      setError(err);
    };

    userManager.events.addUserLoaded(handleUserLoaded);
    userManager.events.addUserUnloaded(handleUserUnloaded);
    userManager.events.addSilentRenewError(handleSilentRenewError);

    return () => {
      userManager.events.removeUserLoaded(handleUserLoaded);
      userManager.events.removeUserUnloaded(handleUserUnloaded);
      userManager.events.removeSilentRenewError(handleSilentRenewError);
    };
  }, [userManager]);

  const login = useCallback(async () => {
    try {
      setError(null);
      await userManager.signinRedirect();
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Login failed"));
      throw err;
    }
  }, [userManager]);

  const logout = useCallback(async () => {
    try {
      setError(null);
      // ローカルセッション（localStorage）を先に削除し、
      // Keycloak 側のセッション削除に失敗しても確実にログアウトした状態にする
      const currentUser = await userManager.getUser();
      await userManager.removeUser();
      setUser(null);
      // end_session_endpoint に id_token_hint を渡して SSO セッションを即座に無効化。
      // Keycloak 25+ は id_token_hint なしだと確認ページを表示してセッションが残ることがある。
      await userManager.signoutRedirect({
        id_token_hint: currentUser?.id_token,
      });
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Logout failed"));
      throw err;
    }
  }, [userManager]);

  const register = useCallback(() => {
    const registerUrl = `${authority}/protocol/openid-connect/registrations?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=${encodeURIComponent(scope)}`;
    window.location.href = registerUrl;
  }, [authority, clientId, redirectUri, scope]);

  const resetPassword = useCallback(() => {
    const resetUrl = `${authority}/login-actions/reset-credentials?client_id=${clientId}`;
    window.location.href = resetUrl;
  }, [authority, clientId]);

  const configureMFA = useCallback(() => {
    if (!user) {
      throw new Error("User must be authenticated to configure MFA");
    }
    const mfaUrl = `${authority}/account/totp`;
    window.location.href = mfaUrl;
  }, [authority, user]);

  const getAccessToken = useCallback(() => {
    return user?.access_token || null;
  }, [user]);

  const hasRole = useCallback(
    (role: string): boolean => {
      if (!user) return false;
      return extractRealmRoles(user).includes(role);
    },
    [user]
  );

  const handleCallback = useCallback(async () => {
    try {
      setError(null);
      const callbackUser = await userManager.signinRedirectCallback();
      setUser(callbackUser);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Callback processing failed"));
      throw err;
    }
  }, [userManager]);

  const contextValue = useMemo(
    () => ({
      user,
      isAuthenticated: !!user && !user.expired,
      isLoading,
      error,
      login,
      logout,
      register,
      resetPassword,
      configureMFA,
      handleCallback,
      getAccessToken,
      hasRole,
    }),
    [user, isLoading, error, login, logout, register, resetPassword, configureMFA, handleCallback, getAccessToken, hasRole]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}
