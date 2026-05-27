import { useEffect, useMemo, useState } from "react";
import {
  fetchMatchPlayers,
  fetchMatches,
  fetchPlayerAnalytics,
} from "../lib/analyticsApi.js";
import FatigueTimeline from "../components/FatigueTimeline.jsx";
import { PassDetailPanel, ShotDetailPanel } from "../components/EventDetailPanel.jsx";

function playerLabel(p) {
  const name = p.player_name || [p.first_name, p.last_name].filter(Boolean).join(" ");
  if (name) return `${name} (#${p.jersey})`;
  if (p.dfl_player_id) return `${p.dfl_player_id} (#${p.jersey})`;
  return `Jersey #${p.jersey}`;
}

export default function Performance() {
  const [matches, setMatches] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedMatchId, setSelectedMatchId] = useState("union_bayern");
  const [selectedTeamFlag, setSelectedTeamFlag] = useState(1);
  const [selectedPlayerKey, setSelectedPlayerKey] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [playersLoading, setPlayersLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedPassId, setSelectedPassId] = useState(null);
  const [selectedShotIndex, setSelectedShotIndex] = useState(0);

  useEffect(() => {
    fetchMatches()
      .then((res) => {
        const rows = res.matches || [];
        setMatches(rows);
        if (rows.length && !rows.find((m) => m.id === selectedMatchId)) {
          setSelectedMatchId(rows[0].id);
        }
      })
      .catch((e) => setError(e.message));
  }, [selectedMatchId]);

  useEffect(() => {
    let cancelled = false;
    setPlayersLoading(true);
    setError("");

    fetchMatchPlayers(selectedMatchId)
      .then((res) => {
        if (cancelled) return;
        const rows = (res.players || []).filter((p) => p.jersey != null && p.team_flag != null);
        setPlayers(rows);

        const teamRows = rows.filter((p) => Number(p.team_flag) === Number(selectedTeamFlag));
        const fallbackTeamRows = rows.filter((p) => Number(p.team_flag) === 1);
        const chosenRows = teamRows.length ? teamRows : fallbackTeamRows.length ? fallbackTeamRows : rows;
        const first = chosenRows[0];
        if (first) {
          setSelectedTeamFlag(Number(first.team_flag));
          setSelectedPlayerKey(`${first.jersey}-${first.team_flag}`);
        } else {
          setSelectedPlayerKey("");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setPlayersLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMatchId]);

  const selectedMatch = useMemo(
    () => matches.find((m) => m.id === selectedMatchId) || null,
    [matches, selectedMatchId],
  );

  const teams = useMemo(() => {
    const hasHome = players.some((p) => Number(p.team_flag) === 1);
    const hasAway = players.some((p) => Number(p.team_flag) === 0);
    const rows = [];
    if (hasHome) rows.push({ team_flag: 1, label: selectedMatch?.home_team || "Home" });
    if (hasAway) rows.push({ team_flag: 0, label: selectedMatch?.away_team || "Away" });
    return rows;
  }, [players, selectedMatch]);

  const teamPlayers = useMemo(() => {
    return players
      .filter((p) => Number(p.team_flag) === Number(selectedTeamFlag))
      .sort((a, b) => Number(a.jersey) - Number(b.jersey));
  }, [players, selectedTeamFlag]);

  useEffect(() => {
    if (!teamPlayers.length) {
      setSelectedPlayerKey("");
      return;
    }
    const exists = teamPlayers.some(
      (p) => `${p.jersey}-${p.team_flag}` === selectedPlayerKey,
    );
    if (!exists) {
      const first = teamPlayers[0];
      setSelectedPlayerKey(`${first.jersey}-${first.team_flag}`);
    }
  }, [teamPlayers, selectedPlayerKey]);

  const selectedPlayer = useMemo(() => {
    const [jersey, team] = (selectedPlayerKey || "").split("-");
    return (
      players.find(
        (p) => Number(p.jersey) === Number(jersey) && Number(p.team_flag) === Number(team),
      ) || null
    );
  }, [players, selectedPlayerKey]);

  useEffect(() => {
    if (!selectedPlayer) {
      setData(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");

    fetchPlayerAnalytics(selectedMatchId, selectedPlayer.jersey, {
      team: selectedPlayer.team_flag,
      playerId: selectedPlayer.dfl_player_id || null,
    })
      .then((body) => {
        if (cancelled) return;
        setData(body);
        setSelectedPassId(body.passes?.[0]?.event_id ?? null);
        setSelectedShotIndex(0);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMatchId, selectedPlayer]);

  const selectedPass = useMemo(
    () => data?.passes?.find((p) => p.event_id === selectedPassId) ?? null,
    [data, selectedPassId],
  );

  const shots = data?.shots || [];
  const selectedShot = shots[selectedShotIndex] ?? null;
  const matchLabel = selectedMatch?.label || selectedMatchId;

  return (
    <div className="performance-page">
      <header className="performance-page__header">
        <h1 className="performance-page__title">Performance</h1>
        <p className="performance-page__lead">
          Fatigue timeline, degradation episodes, and event-level biomechanics.
        </p>
      </header>

      <section className="performance-card">
        <label className="performance-field">
          <span className="performance-field__label">Match</span>
          <select
            className="performance-select"
            value={selectedMatchId}
            onChange={(e) => setSelectedMatchId(e.target.value)}
          >
            {matches.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label || m.id}
              </option>
            ))}
          </select>
        </label>

        <div className="performance-select-grid">
          <label className="performance-field">
            <span className="performance-field__label">Team</span>
            <select
              className="performance-select"
              value={selectedTeamFlag}
              onChange={(e) => setSelectedTeamFlag(Number(e.target.value))}
              disabled={!teams.length}
            >
              {teams.map((t) => (
                <option key={t.team_flag} value={t.team_flag}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>

          <label className="performance-field">
            <span className="performance-field__label">Player</span>
            <select
              className="performance-select"
              value={selectedPlayerKey}
              onChange={(e) => setSelectedPlayerKey(e.target.value)}
              disabled={!teamPlayers.length}
            >
              {teamPlayers.map((p) => (
                <option key={`${p.jersey}-${p.team_flag}`} value={`${p.jersey}-${p.team_flag}`}>
                  {playerLabel(p)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {selectedPlayer && (
          <p className="performance-demo">
            Player: <strong>{playerLabel(selectedPlayer)}</strong>
            {" · "}
            team <strong>{selectedTeamFlag === 1 ? "home" : "away"}</strong>
            {" · "}
            <code>{selectedPlayer.dfl_player_id || "no_dfl_id"}</code>
          </p>
        )}

        {playersLoading && (
          <p className="performance-status">Loading players for selected match…</p>
        )}
        {loading && (
          <p className="performance-status">
            Loading analytics… (uses precomputed S3 cache when available)
          </p>
        )}
        {error && <p className="performance-error">{error}</p>}
      </section>

      {data && selectedPlayer && (
        <>
          <section className="performance-card">
            <h2 className="performance-card__title">Timeline</h2>
            <p className="performance-card__text">
              <strong>Lean Δ (°)</strong> — trunk lean at each ~5s sample minus kickoff baseline.
              Shaded bands are sustained <strong>degradation episodes</strong>. Dots are{" "}
              <strong>notable passes</strong> (stride/lean vs baseline, episode-aware).
            </p>
            <FatigueTimeline
              curve={data.fatigue?.curve || []}
              episodes={data.degradation_episodes || []}
              baseline={data.fatigue?.baseline || {}}
              passes={data.passes || []}
              selectedPassId={selectedPassId}
              onSelectPass={(p) => setSelectedPassId(p.event_id)}
            />
            {data.fatigue?.summary && (
              <p className="detail-note">
                Match summary: final lean drift {data.fatigue.summary.drift_lean}° · signal{" "}
                {data.fatigue.summary.final_signal} · {data.degradation_episodes?.length ?? 0}{" "}
                episodes
              </p>
            )}
          </section>

          <div className="performance-grid">
            <section className="performance-card">
              <h2 className="performance-card__title">Notable passes</h2>
              <p className="performance-card__text">
                {data.passes_summary?.notable_count ?? 0} notable of{" "}
                {data.passes_summary?.total_passes ?? 0} total passes.
              </p>
              <div className="pass-table-wrap">
                <table className="pass-table">
                  <thead>
                    <tr>
                      <th>Min</th>
                      <th>Eval</th>
                      <th>Lean Δ°</th>
                      <th>Stride Δ m</th>
                      <th>Episode</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.passes || []).map((p) => (
                      <tr
                        key={p.event_id}
                        className={
                          p.event_id === selectedPassId ? "pass-table__row--active" : ""
                        }
                        onClick={() => setSelectedPassId(p.event_id)}
                      >
                        <td>{p.minute?.toFixed?.(1) ?? "—"}</td>
                        <td>{p.evaluation ?? "—"}</td>
                        <td>{p.deltas?.lean ?? "—"}</td>
                        <td>{p.deltas?.stride ?? "—"}</td>
                        <td>{p.in_episode ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="performance-card">
              <h2 className="performance-card__title">Pass detail</h2>
              <PassDetailPanel
                pass={selectedPass}
                episodes={data.degradation_episodes || []}
                baseline={data.fatigue?.baseline || {}}
              />
            </section>
          </div>

          <section className="performance-card">
            <h2 className="performance-card__title">Shots</h2>
            {shots.length === 0 ? (
              <p className="performance-card__text">
                No shots for this player in <strong>{matchLabel}</strong> (no matching{" "}
                <code>ShotAtGoal</code> events in the feed).
              </p>
            ) : (
              <>
                <div className="shot-tabs">
                  {shots.map((s, i) => (
                    <button
                      key={s.event_id || i}
                      type="button"
                      className={`shot-tab${i === selectedShotIndex ? " shot-tab--active" : ""}`}
                      onClick={() => setSelectedShotIndex(i)}
                    >
                      {s.minute?.toFixed?.(1) ?? "?"}&apos; — {s.outcome}
                    </button>
                  ))}
                </div>
                <ShotDetailPanel shot={selectedShot} baseline={data.fatigue?.baseline || {}} />
              </>
            )}
          </section>

          <section className="performance-card performance-card--muted">
            <h2 className="performance-card__title">Attribute glossary</h2>
            <ul className="glossary">
              <li>
                <strong>Lean Δ</strong> — trunk lean (°) minus kickoff baseline; positive ≈ more
                forward lean.
              </li>
              <li>
                <strong>Stride Δ</strong> — ankle separation (m) vs baseline; negative ≈ shorter
                stride.
              </li>
              <li>
                <strong>Degradation episode</strong> — consecutive ~5s samples with elevated lean
                or reduced stride.
              </li>
              <li>
                <strong>xPass / pressure</strong> — KPI fields joined by <code>event_id</code>.
              </li>
              <li>
                <strong>Distance (pass)</strong> — DFL band (short / medium / long), not metres.
              </li>
              <li>
                <strong>Angle (shot)</strong> — angle to goal from KPI; separate from trunk lean.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
