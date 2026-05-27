const MARGIN = { top: 28, right: 24, bottom: 40, left: 52 };

function scale(value, min, max, rangeMin, rangeMax) {
  if (max === min) return (rangeMin + rangeMax) / 2;
  return rangeMin + ((value - min) / (max - min)) * (rangeMax - rangeMin);
}

export default function FatigueTimeline({
  curve = [],
  episodes = [],
  baseline = {},
  passes = [],
  selectedPassId,
  onSelectPass,
  width = 920,
  height = 280,
}) {
  const plotW = width - MARGIN.left - MARGIN.right;
  const plotH = height - MARGIN.top - MARGIN.bottom;

  const minutes = curve.map((s) => s.minute).filter((m) => m != null);
  const leanDeltas = curve.map((s) => s.lean_delta).filter((v) => v != null);
  const maxMinute = Math.max(90, ...(minutes.length ? minutes : [90]));
  const yMin = Math.min(-2, ...(leanDeltas.length ? leanDeltas : [-2]));
  const yMax = Math.max(6, ...(leanDeltas.length ? leanDeltas : [6]));

  const x = (minute) => MARGIN.left + scale(minute, 0, maxMinute, 0, plotW);
  const y = (val) => MARGIN.top + scale(val, yMax, yMin, 0, plotH);

  const linePoints = curve
    .filter((s) => s.minute != null && s.lean_delta != null)
    .map((s) => `${x(s.minute).toFixed(1)},${y(s.lean_delta).toFixed(1)}`)
    .join(" ");

  return (
    <div className="timeline-wrap">
      <svg
        className="timeline-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Trunk lean delta over match time with degradation episodes"
      >
        <text x={MARGIN.left} y={16} className="timeline-chart__title">
          Trunk lean vs kickoff baseline (°)
          {baseline.lean != null ? ` — baseline ${baseline.lean}°` : ""}
        </text>

        {[0, 15, 30, 45, 60, 75, 90].map((m) => (
          <g key={`grid-${m}`}>
            <line
              x1={x(m)}
              y1={MARGIN.top}
              x2={x(m)}
              y2={MARGIN.top + plotH}
              className="timeline-chart__grid"
            />
            <text x={x(m)} y={height - 8} textAnchor="middle" className="timeline-chart__axis">
              {m}&apos;
            </text>
          </g>
        ))}

        <line
          x1={MARGIN.left}
          y1={y(0)}
          x2={MARGIN.left + plotW}
          y2={y(0)}
          className="timeline-chart__baseline"
        />
        <text x={8} y={y(0) + 4} className="timeline-chart__ylabel">
          0°
        </text>

        {episodes.map((ep, i) => {
          const x1 = x(ep.start_minute ?? 0);
          const x2 = x(ep.end_minute ?? ep.start_minute ?? 0);
          return (
            <rect
              key={`ep-${i}`}
              x={Math.min(x1, x2)}
              y={MARGIN.top}
              width={Math.max(2, Math.abs(x2 - x1))}
              height={plotH}
              className={`timeline-chart__episode timeline-chart__episode--${ep.severity || "mild"}`}
            />
          );
        })}

        {linePoints && (
          <polyline points={linePoints} className="timeline-chart__line" fill="none" />
        )}

        {passes.map((p) => {
          if (p.minute == null) return null;
          const cx = x(p.minute);
          const cy = y(p.deltas?.lean ?? 0);
          const active = p.event_id === selectedPassId;
          return (
            <circle
              key={p.event_id}
              cx={cx}
              cy={cy}
              r={active ? 7 : 5}
              className={`timeline-chart__pass${active ? " timeline-chart__pass--active" : ""}`}
              onClick={() => onSelectPass?.(p)}
            />
          );
        })}
      </svg>
      <div className="timeline-legend">
        <span className="timeline-legend__item">
          <span className="timeline-legend__swatch timeline-legend__swatch--line" /> Lean Δ curve
        </span>
        <span className="timeline-legend__item">
          <span className="timeline-legend__swatch timeline-legend__swatch--episode" /> Degradation
          window
        </span>
        <span className="timeline-legend__item">
          <span className="timeline-legend__swatch timeline-legend__swatch--pass" /> Notable pass
        </span>
      </div>
    </div>
  );
}
