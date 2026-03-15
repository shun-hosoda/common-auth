import { renderHook } from "@testing-library/react";
import { useAuth } from "./useAuth";
import { AuthContext } from "./AuthContext";
import type { AuthContextValue } from "./types";

const mockContextValue: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
  resetPassword: jest.fn(),
  configureMFA: jest.fn(),
  handleCallback: jest.fn(),
  getAccessToken: jest.fn(),
  hasRole: jest.fn(),
};

describe("useAuth", () => {
  it("throws error when used outside AuthProvider", () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow("useAuth must be used within an AuthProvider");
  });

  it("returns context value when used inside AuthProvider", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthContext.Provider value={mockContextValue}>
        {children}
      </AuthContext.Provider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it("returns authenticated state correctly", () => {
    const authenticatedContext: AuthContextValue = {
      ...mockContextValue,
      isAuthenticated: true,
      user: { expired: false, access_token: "test-token" } as any,
    };

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthContext.Provider value={authenticatedContext}>
        {children}
      </AuthContext.Provider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).not.toBeNull();
  });
});
