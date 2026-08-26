import { useCallback, useEffect, useMemo, useState } from "react";
import {
  acceptInvitation,
  fetchAccessState,
  fetchDashboard,
  sendInvitation,
} from "../lib/analyticsApi.js";

export default function Dashboard() {
  const [standingsView, setStandingsView] = useState("qualifiers");
  const [access, setAccess] = useState(null);
  const [viewingId, setViewingId] = useState("");
  const [viewing, setViewing] = useState(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteResult, setInviteResult] = useState("");
  const [accessError, setAccessError] = useState("");
  const [loadingAccess, setLoadingAccess] = useState(true);
  const [sendingInvite, setSendingInvite] = useState(false);
  const [acceptingId, setAcceptingId] = useState("");

  const imageSrc = useMemo(() => {
    if (standingsView === "middle") return "/middle.png";
    if (standingsView === "lower") return "/lower.png";
    return "/champions.png";
  }, [standingsView]);

  const loadAccess = useCallback(async () => {
    const next = await fetchAccessState();
    setAccess(next);
    setViewingId((current) => current || next.user_id);
    return next;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingAccess(true);
    loadAccess()
      .catch((e) => {
        if (!cancelled) setAccessError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingAccess(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loadAccess]);

  // Resolving the selection server-side is the point: the switcher is a
  // convenience, the 403 is the actual boundary.
  useEffect(() => {
    if (!viewingId) return undefined;
    let cancelled = false;
    fetchDashboard(viewingId)
      .then((res) => {
        if (!cancelled) {
          setViewing(res);
          setAccessError("");
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setViewing(null);
          setAccessError(e.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [viewingId]);

  async function handleSendInvite(e) {
    e.preventDefault();
    setInviteResult("");
    setAccessError("");
    try {
      setSendingInvite(true);
      const res = await sendInvitation(inviteEmail.trim());
      setInviteResult(
        res.already_existed
          ? `${res.email} was already invited (${res.status}).`
          : `Invitation sent to ${res.email}.`,
      );
      setInviteEmail("");
      await loadAccess();
    } catch (err) {
      setAccessError(err.message || String(err));
    } finally {
      setSendingInvite(false);
    }
  }

  async function handleAcceptInvite(invitationId, ownerEmail) {
    setInviteResult("");
    setAccessError("");
    try {
      setAcceptingId(invitationId);
      await acceptInvitation(invitationId);
      setInviteResult(`You can now view ${ownerEmail}'s dashboard.`);
      await loadAccess();
    } catch (err) {
      setAccessError(err.message || String(err));
    } finally {
      setAcceptingId("");
    }
  }

  const viewable = access?.viewable_dashboards || [];
  const received = access?.received || [];
  const sent = access?.sent || [];
  const pendingReceived = received.filter((r) => r.status === "pending");

  return (
    <div className="dashboard-page">
      <div className="dashboard-page__head">
        <h1 className="dashboard-page__title">Dashboard</h1>
        {viewable.length > 1 ? (
          <label className="dashboard-card__select-wrap">
            <span className="sr-only">Viewing dashboard</span>
            <select
              className="dashboard-card__select"
              value={viewingId}
              onChange={(e) => setViewingId(e.target.value)}
            >
              {viewable.map((d) => (
                <option key={d.user_id} value={d.user_id}>
                  {d.is_self ? "My dashboard" : d.email}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {viewing && !viewing.is_self ? (
        <p className="dashboard-viewing">
          Viewing <strong>{viewing.owner_email}</strong>&rsquo;s dashboard, shared with you.
        </p>
      ) : null}

      <div className="dashboard-cards">
        <section className="dashboard-card dashboard-card--standings">
          <div className="dashboard-card__header">
            <h2>Bundesliga Standings</h2>
            <label className="dashboard-card__select-wrap">
              <span className="sr-only">Standings range</span>
              <select
                value={standingsView}
                onChange={(e) => setStandingsView(e.target.value)}
                className="dashboard-card__select"
              >
                <option value="qualifiers">European qualifiers</option>
                <option value="middle">Middle table</option>
                <option value="lower">Lower table / Relegation</option>
              </select>
            </label>
          </div>
          <img
            className="dashboard-standings-image"
            src={imageSrc}
            alt="Bundesliga standings segment"
          />
        </section>

        <section className="dashboard-card dashboard-card--invites">
          <div className="dashboard-card__header">
            <h2>Invitations</h2>
          </div>

          {loadingAccess ? (
            <p className="dashboard-muted">Loading access...</p>
          ) : (
            <>
              {accessError ? <p className="dashboard-error">{accessError}</p> : null}
              {inviteResult ? <p className="dashboard-success">{inviteResult}</p> : null}

              <p className="dashboard-muted">
                Invite a registered user to view your dashboard.
              </p>

              <form className="invite-form" onSubmit={handleSendInvite}>
                <input
                  type="email"
                  className="invite-input"
                  placeholder="user@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
                <button className="invite-btn" type="submit" disabled={sendingInvite}>
                  {sendingInvite ? "Sending..." : "Send invite"}
                </button>
              </form>

              {pendingReceived.length ? (
                <div className="invite-block">
                  <h3>Invitations for you</h3>
                  <ul className="invite-rows">
                    {pendingReceived.map((r) => (
                      <li key={r.id} className="invite-row">
                        <span className="invite-row__email">{r.owner_email}</span>
                        <button
                          className="invite-btn invite-btn--small"
                          type="button"
                          onClick={() => handleAcceptInvite(r.id, r.owner_email)}
                          disabled={acceptingId === r.id}
                        >
                          {acceptingId === r.id ? "Accepting..." : "Accept"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="invite-lists">
                <div>
                  <h3>You shared with</h3>
                  <ul>
                    {sent.map((s) => (
                      <li key={s.id}>
                        {s.email} <span className="invite-status">{s.status}</span>
                      </li>
                    ))}
                    {!sent.length ? <li className="invite-empty">Nobody yet</li> : null}
                  </ul>
                </div>
                <div>
                  <h3>Shared with you</h3>
                  <ul>
                    {received.map((r) => (
                      <li key={r.id}>
                        {r.owner_email} <span className="invite-status">{r.status}</span>
                      </li>
                    ))}
                    {!received.length ? (
                      <li className="invite-empty">Nobody yet</li>
                    ) : null}
                  </ul>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
