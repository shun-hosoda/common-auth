import { render, screen } from "@testing-library/react";
import { AuthGuard } from "./AuthGuard";
import { AuthContext } from "./AuthContext";
import type { AuthContextValue } from "./types";

const createMockContext = (overrides: Partial<AuthContextValue> = {}): AuthContextValue => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  resetPassword: jest.fn(),
  configureMFA: jest.fn(),
  getAccessToken: jest.fn(),
  handleCallback: jest.fn(),
  hasRole: jest.fn().mockReturnValue(false),
  ...overrides,
});

describe("AuthGuard", () => {
  it("shows loading state when isLoading is true", () => {
    const mockContext = createMockContext({ isLoading: true });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("shows custom fallback when loading", () => {
    const mockContext = createMockContext({ isLoading: true });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard fallback={<div>Custom Loading</div>}>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Custom Loading")).toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    const mockContext = createMockContext({ isAuthenticated: true });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("calls login when not authenticated and no onUnauthenticated", () => {
    const loginMock = jest.fn();
    const mockContext = createMockContext({ login: loginMock });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(loginMock).toHaveBeenCalled();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("calls onUnauthenticated when provided and not authenticated", () => {
    const onUnauthenticatedMock = jest.fn();
    const loginMock = jest.fn();
    const mockContext = createMockContext({ login: loginMock });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard onUnauthenticated={onUnauthenticatedMock}>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(onUnauthenticatedMock).toHaveBeenCalled();
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("renders children when authenticated and has required role", () => {
    const mockContext = createMockContext({
      isAuthenticated: true,
      hasRole: jest.fn().mockReturnValue(true),
    });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard requiredRoles={["tenant_admin"]}>
          <div>Admin Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Admin Content")).toBeInTheDocument();
  });

  it("shows Access Denied when authenticated but lacks required role", () => {
    const mockContext = createMockContext({
      isAuthenticated: true,
      hasRole: jest.fn().mockReturnValue(false),
    });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard requiredRoles={["tenant_admin"]}>
          <div>Admin Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });

  it("shows custom unauthorizedFallback when lacking required role", () => {
    const mockContext = createMockContext({
      isAuthenticated: true,
      hasRole: jest.fn().mockReturnValue(false),
    });

    render(
      <AuthContext.Provider value={mockContext}>
        <AuthGuard
          requiredRoles={["super_admin"]}
          unauthorizedFallback={<div>No Permission</div>}
        >
          <div>Super Admin Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("No Permission")).toBeInTheDocument();
    expect(screen.queryByText("Super Admin Content")).not.toBeInTheDocument();
  });
});
