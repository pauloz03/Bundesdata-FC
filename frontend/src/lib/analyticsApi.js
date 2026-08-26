/**
 * FastAPI analytics service (port 8000). In dev, Vite proxies /matches and /health.
 */
import { getAccessToken, redirectToLogin, refreshSession } from "./api.js";

export const analyticsBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_ANALYTICS_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
})();

function authHeaders() {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Attaches the bearer token itself and retries once after a refresh.
 *
 * authHeaders() is spread last and re-read on every attempt: callers must not
 * pass their own Authorization header, or a stale token captured before the
 * refresh would overwrite the fresh one and the retry would 401 again.
 */
async function authorizedFetch(url, options = {}) {
  const { headers: extraHeaders = {}, ...rest } = options;
  const send = () =>
    fetch(url, { ...rest, headers: { ...extraHeaders, ...authHeaders() } });

  let res = await send();
  if (res.status === 401) {
    if (await refreshSession()) {
      res = await send();
    }
    // Only bounce once the session is actually gone. A refresh that failed on a
    // network blip leaves the tokens in place, so surface the error instead of
    // sending a still-valid session to the login page.
    if (res.status === 401 && !getAccessToken()) {
      redirectToLogin();
    }
  }
  return res;
}

export async function fetchMatches() {
  const res = await authorizedFetch(`${analyticsBaseUrl}/matches`);
  if (!res.ok) throw new Error(`Failed to load matches (${res.status})`);
  return res.json();
}

export async function fetchMatchPlayers(matchId) {
  const res = await authorizedFetch(`${analyticsBaseUrl}/matches/${matchId}/players`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to load players (${res.status})`);
  }
  return body;
}

export async function fetchPossession(matchId, { recompute = false } = {}) {
  const params = new URLSearchParams();
  if (recompute) params.set("recompute", "true");
  const res = await authorizedFetch(
    `${analyticsBaseUrl}/matches/${matchId}/possession?${params}`,
  );
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to load possession data (${res.status})`);
  }
  return body;
}

export async function fetchPlayerFatigue(
  matchId,
  jersey,
  { team = 1, recompute = false } = {},
) {
  const params = new URLSearchParams({ team: String(team) });
  if (recompute) params.set("recompute", "true");
  const res = await authorizedFetch(
    `${analyticsBaseUrl}/matches/${matchId}/players/${jersey}/fatigue?${params}`,
  );
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to load fatigue data (${res.status})`);
  }
  return body;
}

export async function fetchPlayerAnalytics(
  matchId,
  jersey,
  { team = 1, playerId = null, recompute = false } = {},
) {
  const params = new URLSearchParams({ team: String(team) });
  if (playerId) params.set("player_id", playerId);
  if (recompute) params.set("recompute", "true");
  const res = await authorizedFetch(
    `${analyticsBaseUrl}/matches/${matchId}/players/${jersey}?${params}`,
  );
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to load player data (${res.status})`);
  }
  return body;
}

export async function fetchAccessState() {
  const res = await authorizedFetch(`${analyticsBaseUrl}/users/access`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to load access state (${res.status})`);
  }
  return body;
}

export async function sendInvitation(email) {
  const res = await authorizedFetch(`${analyticsBaseUrl}/users/invitations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to send invitation (${res.status})`);
  }
  return body;
}

export async function acceptInvitation(invitationId) {
  const res = await authorizedFetch(`${analyticsBaseUrl}/users/invitations/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invitation_id: invitationId }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to accept invitation (${res.status})`);
  }
  return body;
}

/** Opens a dashboard by owner id. Rejects with 403 unless access was granted. */
export async function fetchDashboard(ownerId) {
  const res = await authorizedFetch(`${analyticsBaseUrl}/users/${ownerId}/dashboard`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.msg || JSON.stringify(body.detail);
    throw new Error(detail || `Failed to open dashboard (${res.status})`);
  }
  return body;
}
