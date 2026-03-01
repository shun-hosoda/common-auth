# @common-auth/react

React Hooks SDK for common-auth authentication platform.

## Installation

```bash
npm install @common-auth/react
```

## Quick Start

```tsx
import { AuthProvider, useAuth, AuthGuard } from '@common-auth/react';

function App() {
  return (
    <AuthProvider
      authority="http://localhost:8080/realms/common-auth"
      clientId="frontend-app"
      redirectUri="http://localhost:3000/callback"
      postLogoutRedirectUri="http://localhost:3000"
    >
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/callback" element={<Callback />} />
          <Route path="/dashboard" element={
            <AuthGuard>
              <Dashboard />
            </AuthGuard>
          } />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
```

## API

### AuthProvider

Wrap your app with `AuthProvider` to enable authentication.

```tsx
<AuthProvider
  authority="http://localhost:8080/realms/common-auth"
  clientId="frontend-app"
  redirectUri="http://localhost:3000/callback"
  postLogoutRedirectUri="http://localhost:3000"  // optional
  scope="openid profile email"                   // optional
  automaticSilentRenew={true}                    // optional
>
  {children}
</AuthProvider>
```

### useAuth

Access authentication state and methods.

```tsx
function Dashboard() {
  const {
    user,              // OIDC User object
    isAuthenticated,   // boolean
    isLoading,         // boolean
    error,             // Error | null
    login,             // () => Promise<void>
    logout,            // () => Promise<void>
    register,          // () => void - redirect to Keycloak registration
    resetPassword,     // () => void - redirect to password reset
    configureMFA,      // () => void - redirect to MFA setup
    handleCallback,    // () => Promise<void> - process OIDC callback
    getAccessToken,    // () => string | null
  } = useAuth();

  return (
    <div>
      <p>Welcome, {user?.profile.email}</p>
      <button onClick={logout}>Logout</button>
      <button onClick={configureMFA}>Setup MFA</button>
    </div>
  );
}
```

### AuthGuard

Protect routes from unauthenticated access.

```tsx
// Default: redirects to login
<AuthGuard>
  <ProtectedContent />
</AuthGuard>

// Custom loading state
<AuthGuard fallback={<Spinner />}>
  <ProtectedContent />
</AuthGuard>

// Custom redirect handler (e.g., for Next.js)
<AuthGuard onUnauthenticated={() => router.push('/login')}>
  <ProtectedContent />
</AuthGuard>
```

## Handling Callbacks

Create a callback page to handle OIDC redirects:

```tsx
// pages/callback.tsx
import { useEffect } from 'react';
import { useAuth } from '@common-auth/react';

export default function Callback() {
  const { handleCallback } = useAuth();

  useEffect(() => {
    handleCallback()
      .then(() => window.location.href = '/dashboard')
      .catch(console.error);
  }, [handleCallback]);

  return <div>Processing login...</div>;
}
```

**Important**: Always use `useAuth().handleCallback()` instead of creating a separate `UserManager` instance. This ensures consistent token management across the application.

## Requirements

- React 18+
- Keycloak or any OIDC-compliant IdP

## License

MIT
