import { render, screen, act, waitFor } from "@testing-library/react";
import { renderHook, act as hookAct } from "@testing-library/react";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./useAuth";
import type { User } from "oidc-client-ts";

// --- oidc-client-ts mock ---

const mockSigninRedirect = jest.fn();
const mockSigninRedirectCallback = jest.fn();
const mockGetUser = jest.fn();
const mockRemoveUser = jest.fn();
const mockSignoutRedirect = jest.fn();

const eventHandlers: Record<string, Function[]> = {};

const mockEvents = {
  addUserLoaded: jest.fn((cb: Function) => {
    eventHandlers["userLoaded"] = eventHandlers["userLoaded"] || [];
    eventHandlers["userLoaded"].push(cb);
  }),
  addUserUnloaded: jest.fn((cb: Function) => {
    eventHandlers["userUnloaded"] = eventHandlers["userUnloaded"] || [];
    eventHandlers["userUnloaded"].push(cb);
  }),
  addSilentRenewError: jest.fn((cb: Function) => {
    eventHandlers["silentRenewError"] = eventHandlers["silentRenewError"] || [];
    eventHandlers["silentRenewError"].push(cb);
  }),
  removeUserLoaded: jest.fn(),
  removeUserUnloaded: jest.fn(),
  removeSilentRenewError: jest.fn(),
};

jest.mock("oidc-client-ts", () => ({
  UserManager: jest.fn().mockImplementation(() => ({
    getUser: mockGetUser,
    signinRedirect: mockSigninRedirect,
    signinRedirectCallback: mockSigninRedirectCallback,
    removeUser: mockRemoveUser,
    signoutRedirect: mockSignoutRedirect,
    events: mockEvents,
  })),
  WebStorageStateStore: jest.fn().mockImplementation(() => ({})),
}));

// --- Helpers ---

/** Base64url encode (no padding) */
function b64url(obj: Record<string, unknown>): string {
  const json = JSON.stringify(obj);
  // btoa is available in jsdom
  return btoa(json).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Create a fake JWT with the given payload (header & signature are dummy) */
function fakeJwt(payload: Record<string, unknown>): string {
  const header = b64url({ alg: "RS256", typ: "JWT" });
  const body = b64url(payload);
  return `${header}.${body}.fake-signature`;
}

/** Create a mock User object */
function createMockUser(overrides: Partial<User> = {}): User {
  return {
    access_token: fakeJwt({
      realm_access: { roles: ["tenant_user"] },
      sub: "user-1",
      iss: "http://localhost:8080/realms/common-auth",
    }),
    id_token: "fake-id-token",
    token_type: "Bearer",
    scope: "openid profile email",
    profile: {
      sub: "user-1",
      iss: "http://localhost:8080/realms/common-auth",
      aud: "example-app",
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
    },
    expires_in: 3600,
    expired: false,
    scopes: ["openid", "profile", "email"],
    toStorageString: jest.fn(),
    ...overrides,
  } as unknown as User;
}

const defaultProps = {
  authority: "http://localhost:8080/realms/common-auth",
  clientId: "example-app",
  redirectUri: "http://localhost:3000/callback",
};

/** Render AuthProvider with useAuth consumer for testing */
function renderWithAuth(props = defaultProps) {
  let authResult: ReturnType<typeof useAuth> | undefined;

  function Consumer() {
    authResult = useAuth();
    return (
      <div data-testid="consumer">
        {authResult.isLoading ? "loading" : "ready"}
        {authResult.isAuthenticated ? " authenticated" : " anonymous"}
      </div>
    );
  }

  const utils = render(
    <AuthProvider {...props}>
      <Consumer />
    </AuthProvider>
  );

  return { ...utils, getAuth: () => authResult! };
}

// --- Tests ---

beforeEach(() => {
  jest.clearAllMocks();
  // Reset event handlers
  for (const key in eventHandlers) {
    delete eventHandlers[key];
  }
  // Default: no user
  mockGetUser.mockResolvedValue(null);
});

describe("AuthProvider", () => {
  describe("initialization", () => {
    it("starts in loading state then transitions to ready", async () => {
      mockGetUser.mockResolvedValue(null);

      renderWithAuth();

      // Initially loading
      expect(screen.getByTestId("consumer")).toHaveTextContent("loading");

      // After load
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready anonymous");
      });
    });

    it("loads existing user session", async () => {
      const mockUser = createMockUser();
      mockGetUser.mockResolvedValue(mockUser);

      const { getAuth } = renderWithAuth();

      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready authenticated");
      });

      expect(getAuth().user).toBe(mockUser);
    });

    it("sets error if getUser fails", async () => {
      mockGetUser.mockRejectedValue(new Error("session expired"));

      const { getAuth } = renderWithAuth();

      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      expect(getAuth().error?.message).toBe("session expired");
    });
  });

  describe("login", () => {
    it("calls signinRedirect with prompt=login", async () => {
      mockGetUser.mockResolvedValue(null);
      mockSigninRedirect.mockResolvedValue(undefined);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      await act(async () => {
        await getAuth().login();
      });

      expect(mockSigninRedirect).toHaveBeenCalledWith({ prompt: "login" });
    });
  });

  describe("logout", () => {
    it("removes user locally and calls signoutRedirect with id_token_hint", async () => {
      const mockUser = createMockUser();
      mockGetUser.mockResolvedValue(mockUser);
      mockRemoveUser.mockResolvedValue(undefined);
      mockSignoutRedirect.mockResolvedValue(undefined);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      await act(async () => {
        await getAuth().logout();
      });

      expect(mockRemoveUser).toHaveBeenCalled();
      expect(mockSignoutRedirect).toHaveBeenCalledWith({
        id_token_hint: "fake-id-token",
      });
    });
  });

  describe("changePassword", () => {
    it("calls signinRedirect with kc_action=UPDATE_PASSWORD and returnTo state", async () => {
      const mockUser = createMockUser();
      mockGetUser.mockResolvedValue(mockUser);
      mockSigninRedirect.mockResolvedValue(undefined);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      await act(async () => {
        await getAuth().changePassword({ returnTo: "/me/security" });
      });

      expect(mockSigninRedirect).toHaveBeenCalledWith({
        extraQueryParams: { kc_action: "UPDATE_PASSWORD" },
        state: { returnTo: "/me/security" },
      });
    });

    it("calls signinRedirect without state when no returnTo", async () => {
      const mockUser = createMockUser();
      mockGetUser.mockResolvedValue(mockUser);
      mockSigninRedirect.mockResolvedValue(undefined);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      await act(async () => {
        await getAuth().changePassword();
      });

      expect(mockSigninRedirect).toHaveBeenCalledWith({
        extraQueryParams: { kc_action: "UPDATE_PASSWORD" },
        state: undefined,
      });
    });

    it("throws error when user is not authenticated", async () => {
      mockGetUser.mockResolvedValue(null);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      await expect(
        act(async () => {
          await getAuth().changePassword({ returnTo: "/me/security" });
        })
      ).rejects.toThrow("User must be authenticated to change password");
    });
  });

  describe("handleCallback", () => {
    it("returns state with returnTo from signinRedirectCallback", async () => {
      mockGetUser.mockResolvedValue(null);
      const callbackUser = createMockUser({
        state: { returnTo: "/me/security" } as unknown as undefined,
      });
      (callbackUser as any).state = { returnTo: "/me/security" };
      mockSigninRedirectCallback.mockResolvedValue(callbackUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      let result: { returnTo?: string } | undefined;
      await act(async () => {
        result = await getAuth().handleCallback();
      });

      expect(result).toEqual({ returnTo: "/me/security" });
      // The user should now be set
      expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
    });

    it("returns undefined when no state in callback", async () => {
      mockGetUser.mockResolvedValue(null);
      const callbackUser = createMockUser();
      mockSigninRedirectCallback.mockResolvedValue(callbackUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      let result: { returnTo?: string } | undefined;
      await act(async () => {
        result = await getAuth().handleCallback();
      });

      expect(result).toBeUndefined();
    });

    it("falls back to existing user when state is already consumed", async () => {
      mockGetUser.mockResolvedValue(null);
      mockSigninRedirectCallback.mockRejectedValue(new Error("No matching state found"));

      const existingUser = createMockUser();
      mockGetUser
        .mockResolvedValueOnce(null)
        .mockResolvedValueOnce(existingUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      let result: { returnTo?: string } | undefined;
      await act(async () => {
        result = await getAuth().handleCallback();
      });

      expect(result).toBeUndefined();
      expect(getAuth().error).toBeNull();
      expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
    });

    it("throws and sets error when signinRedirectCallback fails and no user fallback", async () => {
      mockGetUser.mockResolvedValue(null);
      mockSigninRedirectCallback.mockRejectedValue(new Error("No matching state found"));

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      let thrownError: Error | undefined;
      await act(async () => {
        try {
          await getAuth().handleCallback();
        } catch (err) {
          thrownError = err as Error;
        }
      });

      expect(thrownError?.message).toBe("No matching state found");
      expect(getAuth().error?.message).toBe("No matching state found");
    });
  });

  describe("hasRole", () => {
    it("returns true when user has the role in access token", async () => {
      const mockUser = createMockUser({
        access_token: fakeJwt({
          realm_access: { roles: ["tenant_user", "tenant_admin"] },
        }),
      });
      mockGetUser.mockResolvedValue(mockUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      expect(getAuth().hasRole("tenant_admin")).toBe(true);
      expect(getAuth().hasRole("tenant_user")).toBe(true);
    });

    it("returns false when user does not have the role", async () => {
      const mockUser = createMockUser({
        access_token: fakeJwt({
          realm_access: { roles: ["tenant_user"] },
        }),
      });
      mockGetUser.mockResolvedValue(mockUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      expect(getAuth().hasRole("super_admin")).toBe(false);
    });

    it("returns false when no user is authenticated", async () => {
      mockGetUser.mockResolvedValue(null);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      expect(getAuth().hasRole("tenant_user")).toBe(false);
    });

    it("falls back to profile realm_access when access_token parsing fails", async () => {
      const mockUser = createMockUser({
        access_token: "invalid-token",
        profile: {
          sub: "user-1",
          iss: "http://localhost:8080",
          aud: "example-app",
          exp: Math.floor(Date.now() / 1000) + 3600,
          iat: Math.floor(Date.now() / 1000),
          realm_access: { roles: ["fallback_role"] },
        } as any,
      });
      mockGetUser.mockResolvedValue(mockUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      expect(getAuth().hasRole("fallback_role")).toBe(true);
    });
  });

  describe("getAccessToken", () => {
    it("returns access token when authenticated", async () => {
      const token = fakeJwt({ sub: "user-1" });
      const mockUser = createMockUser({ access_token: token });
      mockGetUser.mockResolvedValue(mockUser);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      expect(getAuth().getAccessToken()).toBe(token);
    });

    it("returns null when not authenticated", async () => {
      mockGetUser.mockResolvedValue(null);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      expect(getAuth().getAccessToken()).toBeNull();
    });
  });

  describe("event handling", () => {
    it("updates user on userLoaded event", async () => {
      mockGetUser.mockResolvedValue(null);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("anonymous");
      });

      const newUser = createMockUser();
      await act(async () => {
        eventHandlers["userLoaded"]?.forEach((cb) => cb(newUser));
      });

      expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      expect(getAuth().user).toBe(newUser);
    });

    it("clears user on userUnloaded event", async () => {
      const mockUser = createMockUser();
      mockGetUser.mockResolvedValue(mockUser);

      renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("authenticated");
      });

      await act(async () => {
        eventHandlers["userUnloaded"]?.forEach((cb) => cb());
      });

      expect(screen.getByTestId("consumer")).toHaveTextContent("anonymous");
    });

    it("sets error on silentRenewError event", async () => {
      mockGetUser.mockResolvedValue(null);

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      await act(async () => {
        eventHandlers["silentRenewError"]?.forEach((cb) =>
          cb(new Error("Token refresh failed"))
        );
      });

      expect(getAuth().error?.message).toBe("Token refresh failed");
    });

    it("removes event listeners on unmount", async () => {
      mockGetUser.mockResolvedValue(null);

      const { unmount } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      unmount();

      expect(mockEvents.removeUserLoaded).toHaveBeenCalled();
      expect(mockEvents.removeUserUnloaded).toHaveBeenCalled();
      expect(mockEvents.removeSilentRenewError).toHaveBeenCalled();
    });
  });

  describe("register", () => {
    it("redirects to Keycloak registration endpoint", async () => {
      mockGetUser.mockResolvedValue(null);

      // Mock window.location.href
      const originalLocation = window.location;
      const mockLocation = { ...originalLocation, href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      act(() => {
        getAuth().register();
      });

      expect(mockLocation.href).toContain(
        "http://localhost:8080/realms/common-auth/protocol/openid-connect/registrations"
      );
      expect(mockLocation.href).toContain("client_id=example-app");
      expect(mockLocation.href).toContain(encodeURIComponent("http://localhost:3000/callback"));

      // Restore
      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
      });
    });
  });

  describe("resetPassword", () => {
    it("redirects to Keycloak reset credentials endpoint", async () => {
      mockGetUser.mockResolvedValue(null);

      const originalLocation = window.location;
      const mockLocation = { ...originalLocation, href: "" };
      Object.defineProperty(window, "location", {
        value: mockLocation,
        writable: true,
      });

      const { getAuth } = renderWithAuth();
      await waitFor(() => {
        expect(screen.getByTestId("consumer")).toHaveTextContent("ready");
      });

      act(() => {
        getAuth().resetPassword();
      });

      expect(mockLocation.href).toContain(
        "http://localhost:8080/realms/common-auth/login-actions/reset-credentials"
      );
      expect(mockLocation.href).toContain("client_id=example-app");

      Object.defineProperty(window, "location", {
        value: originalLocation,
        writable: true,
      });
    });
  });
});
