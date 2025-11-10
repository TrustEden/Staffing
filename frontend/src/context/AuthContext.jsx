import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

import { login as loginService } from "../services/auth";
import { fetchCurrentUser } from "../services/backend";
import { clearSession, getSession, saveSession } from "../services/session";

const AuthContext = createContext({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  refreshProfile: async () => {},
  error: null,
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadProfile = useCallback(async () => {
    try {
      const profile = await fetchCurrentUser();
      setUser(profile);
      setError(null);
    } catch (err) {
      console.error("Failed to load profile", err);
      clearSession();
      setUser(null);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const session = getSession();
    if (!session) {
      setLoading(false);
      return;
    }
    loadProfile();
  }, [loadProfile]);

  const login = useCallback(
    async (email, password) => {
      setLoading(true);
      try {
        const tokenResponse = await loginService(email, password);
        saveSession(tokenResponse);
        await loadProfile();
      } catch (err) {
        console.error("Login failed", err);
        clearSession();
        setUser(null);
        setLoading(false);
        setError(err);
        throw err;
      }
    },
    [loadProfile]
  );

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      refreshProfile: loadProfile,
    }),
    [user, loading, error, login, logout, loadProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useAuthContext() {
  return useContext(AuthContext);
}
