import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getAccessToken, getStoredEmail, logout } from "../lib/api.js";

function DashboardIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.5" y="2.5" width="6" height="7.5" rx="1.4" />
      <rect x="2.5" y="13" width="6" height="4.5" rx="1.4" />
      <rect x="11.5" y="2.5" width="6" height="4.5" rx="1.4" />
      <rect x="11.5" y="10" width="6" height="7.5" rx="1.4" />
    </svg>
  );
}

function PerformanceIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2.5 15.5V4" />
      <path d="M2.5 15.5h15" />
      <path d="M5.5 12.5l3.5-4 3 2.5 4.5-5.5" />
    </svg>
  );
}

export default function AppLayout() {
  const navigate = useNavigate();
  const token = getAccessToken();
  const label = getStoredEmail() || (token ? "Analyst" : "Local demo");

  async function handleSignOut() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar" aria-label="Primary">
        <div className="app-sidebar__brand">
          <img src="/bundes.jpg" alt="Bundesliga" className="app-sidebar__logo" />
          <div className="app-sidebar__brand-text">
            <div className="app-sidebar__title">Bundesdata FC</div>
          </div>
        </div>

        <nav className="app-sidebar__nav" aria-label="Main">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `app-sidebar__link${isActive ? " app-sidebar__link--active" : ""}`
            }
          >
            <span className="app-sidebar__icon">
              <DashboardIcon />
            </span>
            <span>Dashboard</span>
          </NavLink>
          <NavLink
            to="/performance"
            className={({ isActive }) =>
              `app-sidebar__link${isActive ? " app-sidebar__link--active" : ""}`
            }
          >
            <span className="app-sidebar__icon">
              <PerformanceIcon />
            </span>
            <span>Performance</span>
          </NavLink>
        </nav>

        <div className="app-sidebar__footer">
          <div className="app-sidebar__email" title={label}>
            {label}
          </div>
          <button type="button" className="app-sidebar__signout" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
