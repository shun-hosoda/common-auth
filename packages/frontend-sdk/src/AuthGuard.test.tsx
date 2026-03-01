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
});
