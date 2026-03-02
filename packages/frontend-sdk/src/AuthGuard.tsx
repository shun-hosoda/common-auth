import { useAuth } from "./useAuth";
import type { AuthGuardProps } from "./types";

export function AuthGuard({
  children,
  fallback,
  onUnauthenticated,
  requiredRoles,
  unauthorizedFallback,
}: AuthGuardProps) {
  const { isAuthenticated, isLoading, login, hasRole } = useAuth();

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

  if (requiredRoles && requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some((role) => hasRole(role));
    if (!hasRequiredRole) {
      return <>{unauthorizedFallback || <div>Access Denied</div>}</>;
    }
  }

  return <>{children}</>;
}
