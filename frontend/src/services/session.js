const STORAGE_KEY = "hsb_session";

export function saveSession(tokenResponse) {
  if (!tokenResponse) return;
  const payload = {
    accessToken: tokenResponse.access_token,
    refreshToken: tokenResponse.refresh_token,
    expiresAt: Date.now() + tokenResponse.expires_in * 1000,
    refreshExpiresAt: Date.now() + tokenResponse.refresh_expires_in * 1000,
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  return payload;
}

export function getSession() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.warn("Failed to parse session", error);
    clearSession();
    return null;
  }
}

export function getAccessToken() {
  return getSession()?.accessToken ?? null;
}

export function clearSession() {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function hasValidAccessToken() {
  const session = getSession();
  if (!session) return false;
  return session.expiresAt > Date.now();
}
