import { useCallback, useEffect, useMemo, useState } from "react";
import { UserManager, User } from "oidc-client-ts";
import { AuthContext } from "./AuthContext";
import type { AuthProviderProps } from "./types";

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
      await userManager.signoutRedirect();
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
      getAccessToken,
    }),
    [user, isLoading, error, login, logout, register, resetPassword, configureMFA, getAccessToken]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}
