import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="dashboard-page">
      <h1 className="dashboard-page__title">Dashboard</h1>
      <p className="dashboard-page__lead">
        Welcome to Bundesdata FC. Open the Performance tab to explore fatigue curves, degradation
        episodes, and event biomechanics for the demo player.
      </p>
      <div className="dashboard-cards">
        <div className="dashboard-card">
          <h2>Performance analytics</h2>
          <p>
            Union vs Bayern · Jersey #14 · Trunk lean timeline, notable passes, and KPI-enriched
            event details.
          </p>
          <Link className="auth-button auth-button--primary" to="/performance">
            Open Performance
          </Link>
        </div>
      </div>
    </div>
  );
}
