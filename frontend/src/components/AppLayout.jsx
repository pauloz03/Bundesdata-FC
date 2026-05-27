import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { decodeJwtPayload } from "../lib/jwt.js";

export default function AppLayout() {
  const navigate = useNavigate();
  const token = localStorage.getItem("token");
  const payload = token ? decodeJwtPayload(token) : null;
  const label =
    payload?.email ||
    payload?.["cognito:username"] ||
    payload?.phone_number ||
    "Analyst";

  function handleSignOut() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <div className="app-layout">
      <header className="app-navbar">
        <div className="app-navbar__brand">Bundesdata FC</div>
        <nav className="app-navbar__links" aria-label="Main">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `app-navbar__link${isActive ? " app-navbar__link--active" : ""}`
            }
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/performance"
            className={({ isActive }) =>
              `app-navbar__link${isActive ? " app-navbar__link--active" : ""}`
            }
          >
            Performance
          </NavLink>
        </nav>
        <div className="app-navbar__user">
          <span className="app-navbar__email">{label}</span>
          <button type="button" className="app-navbar__signout" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
