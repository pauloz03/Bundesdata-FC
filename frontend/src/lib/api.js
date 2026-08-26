/**
 * FastAPI base URL (port 8000). In dev, Vite proxies /auth and /users to this target.
 */
export const apiBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_API_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
})();

const ACCESS_KEY = "token";
const REFRESH_KEY = "refresh_token";
const EMAIL_KEY = "email";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredEmail() {
  return localStorage.getItem(EMAIL_KEY);
}

export function isLoggedIn() {
  return Boolean(getAccessToken());
}

export function saveSession({ access_token, refresh_token, email }) {
  if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
  if (email) localStorage.setItem(EMAIL_KEY, email);
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(EMAIL_KEY);
}

function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(", ");
  }
  return body?.message || `Request failed (${status})`;
}

async function parseBody(res) {
  return res.json().catch(() => ({}));
}

export async function signup({ email, password }) {
  const res = await fetch(`${apiBaseUrl}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), password }),
  });
  const body = await parseBody(res);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  return body;
}

export async function login({ email, password }) {
  const res = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), password }),
  });
  const body = await parseBody(res);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  saveSession({
    access_token: body.access_token,
    refresh_token: body.refresh_token,
    email: email.trim().toLowerCase(),
  });
  return body;
}

async function performRefresh() {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;
  let res;
  try {
    res = await fetch(`${apiBaseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
  } catch {
    // Network failure: keep the session, the token may still be valid.
    return false;
  }
  const body = await parseBody(res);
  if (!res.ok) {
    clearSession();
    return false;
  }
  saveSession({
    access_token: body.access_token,
    refresh_token: body.refresh_token,
  });
  return true;
}

let refreshInFlight = null;

/**
 * Single-flight. A page load fires several requests at once, so an expired
 * access token produces a burst of 401s. The server rotates the refresh token
 * on every call, so letting those refresh in parallel would leave the stored
 * token out of sync with the database and lock the user out for good.
 */
export function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = performRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/** Session is unrecoverable — bounce to login. */
export function redirectToLogin() {
  if (window.location.pathname !== "/login") {
    window.location.assign("/login");
  }
}

export async function logout() {
  const access_token = getAccessToken();
  const refresh_token = getRefreshToken();
  try {
    if (access_token && refresh_token) {
      await fetch(`${apiBaseUrl}/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${access_token}`,
        },
        body: JSON.stringify({ refresh_token }),
      });
    }
  } finally {
    clearSession();
  }
}
