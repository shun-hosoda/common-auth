import { useAuth } from "./useAuth";
import type { AuthGuardProps } from "./types";

export function AuthGuard({
  children,
  fallback,
  onUnauthenticated,
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, login } = useAuth();

  if (isLoading) {
    return <>{fallback || <div>Loading...</div>}</>;
  }

  if (!isAuthenticated) {
    if (onUnauthenticated) {
      onUnauthenticated();
      return null;
    }
    login();
    return null;
  }

  return <>{children}</>;
}
