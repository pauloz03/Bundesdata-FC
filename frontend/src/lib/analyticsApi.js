/**
 * FastAPI analytics service (port 8000). In dev, Vite proxies /matches and /health.
 */
export const analyticsBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_ANALYTICS_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
})();

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchMatches() {
  const res = await fetch(`${analyticsBaseUrl}/matches`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to load matches (${res.status})`);
  return res.json();
}

export async function fetchMatchPlayers(matchId) {
  const res = await fetch(`${analyticsBaseUrl}/matches/${matchId}/players`, {
    headers: authHeaders(),
  });
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

export async function fetchPlayerFatigue(
  matchId,
  jersey,
  { team = 1, recompute = false } = {},
) {
  const params = new URLSearchParams({ team: String(team) });
  if (recompute) params.set("recompute", "true");
  const res = await fetch(
    `${analyticsBaseUrl}/matches/${matchId}/players/${jersey}/fatigue?${params}`,
    {
      headers: authHeaders(),
    },
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
  const res = await fetch(
    `${analyticsBaseUrl}/matches/${matchId}/players/${jersey}?${params}`,
    {
      headers: authHeaders(),
    },
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
  const res = await fetch(`${analyticsBaseUrl}/users/access`, {
    headers: authHeaders(),
  });
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
  const res = await fetch(`${analyticsBaseUrl}/users/invitations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
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

export async function acceptInvitation() {
  const res = await fetch(`${analyticsBaseUrl}/users/invitations/accept`, {
    method: "POST",
    headers: authHeaders(),
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
