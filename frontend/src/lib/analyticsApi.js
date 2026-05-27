/**
 * FastAPI analytics service (port 8000). In dev, Vite proxies /matches and /health.
 */
export const analyticsBaseUrl = (() => {
  const fromEnv = import.meta.env.VITE_ANALYTICS_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  if (import.meta.env.DEV) return "";
  return "http://localhost:8000";
})();

export async function fetchMatches() {
  const res = await fetch(`${analyticsBaseUrl}/matches`);
  if (!res.ok) throw new Error(`Failed to load matches (${res.status})`);
  return res.json();
}

export async function fetchMatchPlayers(matchId) {
  const res = await fetch(`${analyticsBaseUrl}/matches/${matchId}/players`);
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
