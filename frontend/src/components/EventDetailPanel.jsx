function Metric({ label, value, unit = "" }) {
  return (
    <div className="metric">
      <dt>{label}</dt>
      <dd>{value != null && value !== "" ? `${value}${unit}` : "—"}</dd>
    </div>
  );
}

function findEpisode(minute, episodes) {
  if (minute == null) return null;
  return (
    episodes.find(
      (ep) =>
        ep.start_minute != null &&
        ep.end_minute != null &&
        minute >= ep.start_minute &&
        minute <= ep.end_minute,
    ) ?? null
  );
}

export function PassDetailPanel({ pass, episodes, baseline }) {
  if (!pass) {
    return (
      <div className="detail-panel detail-panel--empty">
        Select a pass on the timeline or in the list to see biomechanics and event attributes.
      </div>
    );
  }

  const bio = pass.biomechanics || {};
  const ep = findEpisode(pass.minute, episodes);

  return (
    <div className="detail-panel">
      <h3 className="detail-panel__title">
        Pass at {pass.minute?.toFixed?.(1) ?? pass.minute}&apos; — {pass.evaluation || "pass"}
      </h3>

      <section className="detail-section">
        <h4>Skeleton biomechanics (at contact frame)</h4>
        <dl className="metric-grid">
          <Metric label="Trunk lean" value={bio.trunk_lean} unit="°" />
          <Metric label="Δ vs kickoff lean" value={pass.deltas?.lean} unit="°" />
          <Metric label="Stride length" value={bio.stride_length} unit=" m" />
          <Metric label="Δ vs kickoff stride" value={pass.deltas?.stride} unit=" m" />
          <Metric label="Shoulder asymmetry" value={bio.shoulder_asymmetry} />
          <Metric
            label="Knee bend (R / L)"
            value={
              bio.knee_bend_right != null && bio.knee_bend_left != null
                ? `${bio.knee_bend_right}° / ${bio.knee_bend_left}°`
                : null
            }
          />
        </dl>
        {baseline?.lean != null && (
          <p className="detail-note">
            Kickoff baseline: lean {baseline.lean}°, stride {baseline.stride} m
          </p>
        )}
      </section>

      {ep && (
        <section className="detail-section detail-section--episode">
          <h4>Degradation window</h4>
          <p>
            {ep.start_minute?.toFixed?.(1)}&apos; – {ep.end_minute?.toFixed?.(1)}&apos;
            {" · "}
            severity <strong>{ep.severity}</strong>
            {" · "}
            peak lean Δ {ep.peak_lean_delta}°
            {ep.peak_stride_delta != null && (
              <> · peak stride Δ {ep.peak_stride_delta} m</>
            )}
          </p>
        </section>
      )}

      <section className="detail-section">
        <h4>Event & KPI attributes</h4>
        <dl className="metric-grid">
          <Metric label="Event ID" value={pass.event_id} />
          <Metric label="Frame" value={pass.frame_number} />
          <Metric label="Recipient" value={pass.recipient} />
          <Metric label="Height" value={pass.height} />
          <Metric label="Distance (XML band)" value={pass.distance} />
          <Metric label="xPass" value={pass.xpass} />
          <Metric label="Pressure" value={pass.pressure} />
          <Metric label="Player speed" value={pass.player_speed} unit=" km/h" />
          <Metric label="Rotation" value={pass.rotation} />
        </dl>
      </section>

      <section className="detail-section">
        <h4>Notable flags</h4>
        <p>
          {pass.in_episode ? "Inside degradation episode" : "Outside episodes"}
          {pass.notable_reasons?.length > 0 && <> · {pass.notable_reasons.join(", ")}</>}
        </p>
      </section>
    </div>
  );
}

export function ShotDetailPanel({ shot, baseline }) {
  if (!shot) return null;

  const bio = shot.biomechanics || {};

  return (
    <div className="detail-panel">
      <h3 className="detail-panel__title">
        Shot at {shot.minute?.toFixed?.(1) ?? shot.minute}&apos; — {shot.outcome}
      </h3>
      <dl className="metric-grid">
        <Metric label="Trunk lean" value={bio.trunk_lean} unit="°" />
        <Metric label="Stride" value={bio.stride_length} unit=" m" />
        <Metric label="Type of shot" value={shot.type_of_shot} />
        <Metric label="Taker setup" value={shot.taker_setup} />
        <Metric label="Shot origin" value={shot.shot_origin} />
        <Metric label="xG" value={shot.xg} />
        <Metric label="Distance to goal" value={shot.distance_to_goal ?? shot.distance} unit=" m" />
        <Metric label="Angle to goal" value={shot.angle_to_goal ?? shot.angle} unit="°" />
        <Metric label="Pressure" value={shot.pressure} />
        <Metric label="Player speed" value={shot.player_speed} unit=" km/h" />
        <Metric label="Amount of defenders" value={shot.amount_of_defenders} />
        <Metric label="Shot condition" value={shot.shot_condition} />
      </dl>
      {baseline?.lean != null && bio.trunk_lean != null && (
        <p className="detail-note">
          Lean vs kickoff: {(bio.trunk_lean - baseline.lean).toFixed(2)}°
        </p>
      )}
    </div>
  );
}
