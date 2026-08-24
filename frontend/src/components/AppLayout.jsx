import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { decodeJwtPayload } from "../lib/jwt.js";

export default function AppLayout() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");
  const payload = token ? decodeJwtPayload(token) : null;
  const label =
    payload?.email ||
    payload?.phone_number ||
    (token ? "Analyst" : "Local demo");

  function handleSignOut() {
    localStorage.removeItem("token");
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
            <span className="app-sidebar__icon">◻</span>
            <span>Dashboard</span>
          </NavLink>
          <NavLink
            to="/performance"
            className={({ isActive }) =>
              `app-sidebar__link${isActive ? " app-sidebar__link--active" : ""}`
            }
          >
            <span className="app-sidebar__icon">◻</span>
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
