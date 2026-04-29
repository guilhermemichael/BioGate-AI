const ACCESS_TOKEN_KEY = "biogate.accessToken";
const REFRESH_TOKEN_KEY = "biogate.refreshToken";
const SESSION_ID_KEY = "biogate.sessionId";
const USER_KEY = "biogate.user";

export function getAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getSessionId() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(SESSION_ID_KEY);
}

export function setSession(payload: { accessToken: string; refreshToken: string; sessionId?: string; user: object }) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, payload.accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, payload.refreshToken);
  if (payload.sessionId) {
    window.localStorage.setItem(SESSION_ID_KEY, payload.sessionId);
  }
  window.localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

export function clearSession() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(SESSION_ID_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function getStoredUser<T>() {
  if (typeof window === "undefined") {
    return null as T | null;
  }
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null as T | null;
  }
  return JSON.parse(raw) as T;
}

export function buildDeviceFingerprint() {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return "";
  }

  return [
    `ua=${navigator.userAgent}`,
    `lang=${navigator.language}`,
    `platform=${navigator.platform}`,
    `screen=${window.screen.width}x${window.screen.height}`,
    `tz=${Intl.DateTimeFormat().resolvedOptions().timeZone}`,
    `cpu=${navigator.hardwareConcurrency ?? "unknown"}`,
  ].join("|");
}
