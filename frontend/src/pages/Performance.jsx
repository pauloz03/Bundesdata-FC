import { useEffect, useMemo, useState } from "react";
import {
  fetchMatchPlayers,
  fetchMatches,
  fetchPlayerFatigue,
  fetchPossession,
} from "../lib/analyticsApi.js";
import FatigueTimeline from "../components/FatigueTimeline.jsx";
import PossessionPitch from "../components/PossessionPitch.jsx";

function playerLabel(p) {
  const name = p.player_name || [p.first_name, p.last_name].filter(Boolean).join(" ");
  if (name) return `${name} (#${p.jersey})`;
  if (p.dfl_player_id) return `${p.dfl_player_id} (#${p.jersey})`;
  return `Jersey #${p.jersey}`;
}

const TEAM_LOGOS = {
  "fc bayern munich":
    "https://upload.wikimedia.org/wikipedia/en/thumb/1/1f/FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg/240px-FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg.png",
  "bayern munich":
    "https://upload.wikimedia.org/wikipedia/en/thumb/1/1f/FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg/240px-FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg.png",
  "fc union berlin":
    "https://upload.wikimedia.org/wikipedia/en/thumb/4/44/1._FC_Union_Berlin_logo.svg/240px-1._FC_Union_Berlin_logo.svg.png",
  "eintracht frankfurt":
    "https://upload.wikimedia.org/wikipedia/en/thumb/e/e3/Eintracht_Frankfurt_Logo.svg/240px-Eintracht_Frankfurt_Logo.svg.png",
};

function normalizeTeamName(name) {
  return (name || "").toLowerCase().trim();
}

function getTeamLogo(name) {
  return TEAM_LOGOS[normalizeTeamName(name)] || null;
}

function getPlayerAvatar(name) {
  const label = name || "Player";
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(
    label,
  )}&background=0b1220&color=e5e7eb&size=160&bold=true`;
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
  const [possession, setPossession] = useState(null);
  const [possessionLoading, setPossessionLoading] = useState(false);
  const [possessionError, setPossessionError] = useState("");

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

  useEffect(() => {
    let cancelled = false;
    setPossession(null);
    setPossessionError("");
    setPossessionLoading(true);

    fetchPossession(selectedMatchId)
      .then((res) => {
        if (!cancelled) setPossession(res);
      })
      .catch((e) => {
        if (!cancelled) setPossessionError(e.message);
      })
      .finally(() => {
        if (!cancelled) setPossessionLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedMatchId]);

  const selectedMatch = useMemo(
    () => matches.find((m) => m.id === selectedMatchId) || null,
    [matches, selectedMatchId],
  );

  const eventCounts = useMemo(() => {
    const events = possession?.events || [];
    return events.reduce((acc, e) => {
      acc[e.event_type] = (acc[e.event_type] || 0) + 1;
      return acc;
    }, {});
  }, [possession]);

  const teams = useMemo(() => {
    const hasHome = players.some((p) => Number(p.team_flag) === 1);
    const hasAway = players.some((p) => Number(p.team_flag) === 0);
    const rows = [];
    if (hasHome) {
      const homePlayer = players.find((p) => Number(p.team_flag) === 1);
      rows.push({
        team_flag: 1,
        label: selectedMatch?.home_team || "Home",
        logo_url: homePlayer?.team_logo_url || null,
      });
    }
    if (hasAway) {
      const awayPlayer = players.find((p) => Number(p.team_flag) === 0);
      rows.push({
        team_flag: 0,
        label: selectedMatch?.away_team || "Away",
        logo_url: awayPlayer?.team_logo_url || null,
      });
    }
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

    fetchPlayerFatigue(selectedMatchId, selectedPlayer.jersey, {
      team: selectedPlayer.team_flag,
    })
      .then((body) => {
        if (cancelled) return;
        setData(body);
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

  const matchLabel = selectedMatch?.label || selectedMatchId;
  const homeTeam = selectedMatch?.home_team || "Home";
  const awayTeam = selectedMatch?.away_team || "Away";
  const selectedTeamName = selectedTeamFlag === 1 ? homeTeam : awayTeam;
  const homeLogo = teams.find((t) => Number(t.team_flag) === 1)?.logo_url || getTeamLogo(homeTeam);
  const awayLogo = teams.find((t) => Number(t.team_flag) === 0)?.logo_url || getTeamLogo(awayTeam);
  const selectedPlayerName =
    selectedPlayer?.player_name ||
    [selectedPlayer?.first_name, selectedPlayer?.last_name].filter(Boolean).join(" ") ||
    `Jersey #${selectedPlayer?.jersey ?? "?"}`;
  const selectedPlayerAvatar = selectedPlayer?.headshot_url || getPlayerAvatar(selectedPlayerName);

  return (
    <div className="performance-page">
      <section className="performance-hero">
        <header className="performance-page__header">
          <h1 className="performance-page__title">Performance Hub</h1>
        </header>

        <div className="performance-hero__cards">
          <div className="performance-hero__card">
            <h3>Match</h3>
            <p>{matchLabel}</p>
            <div className="team-badges">
              <div className="team-badge">
                {homeLogo ? (
                  <img src={homeLogo} alt={homeTeam} />
                ) : (
                  <span className="team-badge__fallback">{homeTeam.slice(0, 2).toUpperCase()}</span>
                )}
                <span>{homeTeam}</span>
              </div>
              <div className="team-badge">
                {awayLogo ? (
                  <img src={awayLogo} alt={awayTeam} />
                ) : (
                  <span className="team-badge__fallback">{awayTeam.slice(0, 2).toUpperCase()}</span>
                )}
                <span>{awayTeam}</span>
              </div>
            </div>
          </div>

          <div className="performance-hero__card performance-hero__card--player">
            <img
              className="player-avatar"
              src={selectedPlayerAvatar}
              alt={selectedPlayerName}
            />
            <div>
              <h3>Selected Player</h3>
              <p>{selectedPlayerName}</p>
              <small>
                {selectedTeamName} · #{selectedPlayer?.jersey ?? "—"}
              </small>
            </div>
          </div>
        </div>
      </section>

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
            Computing fatigue curve from local parquet…
          </p>
        )}
        {error && <p className="performance-error">{error}</p>}
      </section>

      {data && selectedPlayer && (
        <section className="performance-card">
          <h2 className="performance-card__title">Timeline</h2>
          <p className="performance-card__text">
            <strong>Lean Δ (°)</strong> — trunk lean at each ~5s sample minus kickoff
            baseline. Shaded bands are sustained <strong>degradation episodes</strong>.
          </p>
          <FatigueTimeline
            curve={data.fatigue?.curve || []}
            episodes={data.degradation_episodes || []}
            baseline={data.fatigue?.baseline || {}}
          />
          {data.fatigue?.summary && (
            <p className="detail-note">
              Match summary: final lean drift {data.fatigue.summary.drift_lean}° · signal{" "}
              {data.fatigue.summary.final_signal} · {data.degradation_episodes?.length ?? 0}{" "}
              episodes
            </p>
          )}
        </section>
      )}

      <section className="performance-card performance-card--panel">
        <h2 className="performance-card__title">Possession share</h2>
        <p className="performance-card__text">
          Time each team spent in direct control of the ball, derived from tracking
          data. The pitch is split by <strong>area proportion only</strong>, so it
          does not show where possession happened. Ball-in-flight and out-of-play
          time is excluded, so this won&apos;t match broadcast possession figures.
        </p>

        {possessionLoading && (
          <p className="performance-status">
            Deriving possession from tracking data… (first run per match scans the
            full parquet and takes ~25s)
          </p>
        )}
        {possessionError && <p className="performance-error">{possessionError}</p>}

        {possession?.possession && (
          <>
            <PossessionPitch
              homeTeam={possession.home_team || "Home"}
              awayTeam={possession.away_team || "Away"}
              homePct={possession.possession.home_pct}
              awayPct={possession.possession.away_pct}
              homeSeconds={possession.possession.home_seconds}
              awaySeconds={possession.possession.away_seconds}
            />
            <div className="possession-summary">
              <span>
                Passes{" "}
                <span className="possession-summary__value">{eventCounts.pass || 0}</span>
              </span>
              <span>
                Turnovers{" "}
                <span className="possession-summary__value">
                  {eventCounts.turnover || 0}
                </span>
              </span>
              <span>
                Restarts{" "}
                <span className="possession-summary__value">
                  {eventCounts.restart || 0}
                </span>
              </span>
            </div>
            {possession.unverified && (
              <p className="detail-note">
                Events are derived from ball and player tracking, not vendor labels.
              </p>
            )}
          </>
        )}
      </section>

      {data && selectedPlayer && (
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
              <strong>Baseline</strong> — mean lean, stride and shoulder asymmetry over the
              first 10 samples after kickoff (roughly the opening 50 seconds), taken as the
              player&apos;s fresh posture. Every Δ on this page is measured against it.
            </li>
            <li>
              <strong>Degradation episode</strong> — a sustained run of posture decline, built
              in four steps:
              <ol className="glossary__steps">
                <li>
                  <strong>Sample.</strong> The skeleton stream is read every 250 frames, which
                  is one sample per ~5 seconds at 50Hz. Trunk lean, stride and shoulder
                  asymmetry are computed at each sample and differenced against the baseline.
                </li>
                <li>
                  <strong>Smooth.</strong> A 3-point median filter runs over the lean Δ series,
                  so a single bad skeleton fit or an odd body position (a stretch, a slide,
                  bending to tie a boot) can&apos;t create an episode on its own.
                </li>
                <li>
                  <strong>Flag.</strong> A sample counts as degraded when smoothed lean sits
                  ≥3.0° above baseline <em>or</em> stride has shortened by ≥0.08m. Either
                  signal alone is enough, since players compensate differently as they tire —
                  some fold forward at the trunk, others keep posture but shorten their step.
                </li>
                <li>
                  <strong>Group.</strong> Six consecutive degraded samples (~30 seconds) form
                  an episode. One clean sample is tolerated inside a run, so a brief walk or
                  stoppage doesn&apos;t split a genuine episode in two; two in a row ends it.
                </li>
              </ol>
              The ~30s floor is what separates fatigue from noise. A player leans forward
              constantly during normal play, so only decline that <em>persists</em> across
              roughly half a minute is treated as a real change in movement quality.
            </li>
            <li>
              <strong>Episode severity</strong> — graded on the peak smoothed lean Δ inside the
              episode: <strong>mild</strong> from 0.5°, <strong>moderate</strong> from 2.0°,
              <strong> high</strong> from 5.0°. An episode driven by stride alone is graded
              moderate when the step shortened by ≥0.16m, mild otherwise.
            </li>
          </ul>
        </section>
      )}
    </div>
  );
}
