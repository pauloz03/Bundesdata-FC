/**
 * Possession share as a proportionally divided pitch.
 *
 * The gradient split is a pure area proportion — it does not indicate WHERE on
 * the pitch either team had the ball. Pitch dimensions match the tracking data
 * (105.0m x 67.9m from the parquet file metadata).
 */

const PITCH_L = 105.0;
const PITCH_W = 67.9;
const HALF_L = PITCH_L / 2;
const HALF_W = PITCH_W / 2;

const MARGIN = 2;
const VIEW_W = PITCH_L + MARGIN * 2;
const VIEW_H = PITCH_W + MARGIN * 2;

function formatClock(seconds) {
  if (seconds == null) return null;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function PossessionPitch({
  homeTeam = "Home",
  awayTeam = "Away",
  homePct = 0,
  awayPct = 0,
  homeSeconds = null,
  awaySeconds = null,
}) {
  const total = homePct + awayPct;
  const homeShare = total > 0 ? homePct / total : 0.5;
  const dividerX = -HALF_L + PITCH_L * homeShare;

  // Diverging colour ramp: saturated at each end, neutral where the split sits.
  const stops = [
    [0, "#1d4ed8", 0.78],
    [homeShare * 0.6, "#3b82f6", 0.52],
    [Math.max(0, homeShare - 0.07), "#60a5fa", 0.24],
    [homeShare, "#94a3b8", 0.12],
    [Math.min(1, homeShare + 0.07), "#fb923c", 0.24],
    [homeShare + (1 - homeShare) * 0.4, "#f97316", 0.52],
    [1, "#dc2626", 0.78],
  ];

  return (
    <div className="possession-pitch">
      <svg
        className="possession-pitch__svg"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label={`Possession share: ${homeTeam} ${homePct}%, ${awayTeam} ${awayPct}%`}
      >
        <defs>
          <linearGradient id="possession-heat" x1="0" y1="0" x2="1" y2="0">
            {stops.map(([offset, color, opacity], i) => (
              <stop
                key={i}
                offset={Math.min(1, Math.max(0, offset))}
                stopColor={color}
                stopOpacity={opacity}
              />
            ))}
          </linearGradient>
        </defs>

        <rect
          x={0}
          y={0}
          width={VIEW_W}
          height={VIEW_H}
          className="possession-pitch__bg"
        />

        <g transform={`translate(${VIEW_W / 2}, ${VIEW_H / 2})`}>
          <rect
            x={-HALF_L}
            y={-HALF_W}
            width={PITCH_L}
            height={PITCH_W}
            fill="url(#possession-heat)"
          />

          <g className="possession-pitch__lines">
            <rect x={-HALF_L} y={-HALF_W} width={PITCH_L} height={PITCH_W} />
            <line x1={0} y1={-HALF_W} x2={0} y2={HALF_W} />
            <circle cx={0} cy={0} r={9.15} />
            <rect x={-HALF_L} y={-20.16} width={16.5} height={40.32} />
            <rect x={HALF_L - 16.5} y={-20.16} width={16.5} height={40.32} />
            <rect x={-HALF_L} y={-9.16} width={5.5} height={18.32} />
            <rect x={HALF_L - 5.5} y={-9.16} width={5.5} height={18.32} />
          </g>

          <circle cx={0} cy={0} r={0.45} className="possession-pitch__spot" />
          <circle cx={-HALF_L + 11} cy={0} r={0.45} className="possession-pitch__spot" />
          <circle cx={HALF_L - 11} cy={0} r={0.45} className="possession-pitch__spot" />

          <line
            x1={dividerX}
            y1={-HALF_W}
            x2={dividerX}
            y2={HALF_W}
            className="possession-pitch__divider"
          />

          {homeShare > 0.1 && (
            <text
              x={(-HALF_L + dividerX) / 2}
              y={2.7}
              textAnchor="middle"
              className="possession-pitch__pct"
            >
              {homePct}
              <tspan className="possession-pitch__pct-unit">%</tspan>
            </text>
          )}
          {1 - homeShare > 0.1 && (
            <text
              x={(dividerX + HALF_L) / 2}
              y={2.7}
              textAnchor="middle"
              className="possession-pitch__pct"
            >
              {awayPct}
              <tspan className="possession-pitch__pct-unit">%</tspan>
            </text>
          )}
        </g>
      </svg>

      <div className="possession-pitch__legend">
        <span className="possession-pitch__legend-item">
          <span className="possession-pitch__swatch possession-pitch__swatch--home" />
          {homeTeam}
          {homeSeconds != null ? (
            <span className="possession-pitch__legend-time">{formatClock(homeSeconds)}</span>
          ) : null}
        </span>
        <span className="possession-pitch__legend-item">
          <span className="possession-pitch__swatch possession-pitch__swatch--away" />
          {awayTeam}
          {awaySeconds != null ? (
            <span className="possession-pitch__legend-time">{formatClock(awaySeconds)}</span>
          ) : null}
        </span>
      </div>
    </div>
  );
}
