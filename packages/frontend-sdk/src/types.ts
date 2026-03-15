import type { User } from "oidc-client-ts";

export interface AuthConfig {
  authority: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri?: string;
  scope?: string;
  automaticSilentRenew?: boolean;
}

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;

  login: () => Promise<void>;
  logout: () => Promise<void>;
  register: () => void;
  resetPassword: () => void;
  configureMFA: () => void;
  handleCallback: () => Promise<void>;

  getAccessToken: () => string | null;
  hasRole: (role: string) => boolean;
}

export interface AuthProviderProps extends AuthConfig {
  children: React.ReactNode;
}

export interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onUnauthenticated?: () => void;
  requiredRoles?: string[];
  unauthorizedFallback?: React.ReactNode;
}
