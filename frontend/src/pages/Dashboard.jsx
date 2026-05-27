import { useEffect, useMemo, useState } from "react";
import {
  acceptInvitation,
  fetchAccessState,
  sendInvitation,
} from "../lib/analyticsApi.js";

export default function Dashboard() {
  const [standingsView, setStandingsView] = useState("qualifiers");
  const [access, setAccess] = useState(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteResult, setInviteResult] = useState("");
  const [accessError, setAccessError] = useState("");
  const [loadingAccess, setLoadingAccess] = useState(true);
  const [sendingInvite, setSendingInvite] = useState(false);
  const [acceptingInvite, setAcceptingInvite] = useState(false);

  const imageSrc = useMemo(() => {
    if (standingsView === "middle") return "/middle.png";
    if (standingsView === "lower") return "/lower.png";
    return "/champions.png";
  }, [standingsView]);

  useEffect(() => {
    let cancelled = false;
    setLoadingAccess(true);
    setAccessError("");
    fetchAccessState()
      .then((res) => {
        if (!cancelled) setAccess(res);
      })
      .catch((e) => {
        if (!cancelled) setAccessError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingAccess(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function refreshAccess() {
    setAccessError("");
    const next = await fetchAccessState();
    setAccess(next);
  }

  async function handleSendInvite(e) {
    e.preventDefault();
    setInviteResult("");
    setAccessError("");
    try {
      setSendingInvite(true);
      const res = await sendInvitation(inviteEmail.trim());
      setInviteResult(`Invitation status: ${res.status} (${res.email})`);
      setInviteEmail("");
      await refreshAccess();
    } catch (err) {
      setAccessError(err.message || String(err));
    } finally {
      setSendingInvite(false);
    }
  }

  async function handleAcceptInvite() {
    setInviteResult("");
    setAccessError("");
    try {
      setAcceptingInvite(true);
      const res = await acceptInvitation();
      setInviteResult(`Invitation status: ${res.status}`);
      await refreshAccess();
    } catch (err) {
      setAccessError(err.message || String(err));
    } finally {
      setAcceptingInvite(false);
    }
  }

  return (
    <div className="dashboard-page">
      <h1 className="dashboard-page__title">Dashboard</h1>
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
          <img className="dashboard-standings-image" src={imageSrc} alt="Bundesliga standings segment" />
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
                Your access: <strong>{access?.invitation_status || "unknown"}</strong>
              </p>

              {access?.is_owner ? (
                <>
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

                  <div className="invite-lists">
                    <div>
                      <h3>Pending</h3>
                      <ul>
                        {(access?.pending_invites || []).map((email) => (
                          <li key={email}>{email}</li>
                        ))}
                        {!access?.pending_invites?.length ? <li>None</li> : null}
                      </ul>
                    </div>
                    <div>
                      <h3>Accepted</h3>
                      <ul>
                        {(access?.accepted_invites || []).map((email) => (
                          <li key={email}>{email}</li>
                        ))}
                        {!access?.accepted_invites?.length ? <li>None</li> : null}
                      </ul>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {access?.invitation_status === "pending" ? (
                    <button
                      className="invite-btn"
                      type="button"
                      onClick={handleAcceptInvite}
                      disabled={acceptingInvite}
                    >
                      {acceptingInvite ? "Accepting..." : "Accept invitation"}
                    </button>
                  ) : null}
                  {access?.invitation_status === "none" ? (
                    <p className="dashboard-muted">
                      No invitation found for this account yet.
                    </p>
                  ) : null}
                  {access?.invitation_status === "accepted" ? (
                    <p className="dashboard-success">
                      Invitation accepted. You now have access.
                    </p>
                  ) : null}
                </>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
