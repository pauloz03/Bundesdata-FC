import { Link } from "react-router-dom";

export default function Login() {
  return (
    <div className="auth-stack">
      <div className="auth-app-name">
        <img src="/bundes.jpg" alt="" className="auth-app-name__logo" />
        <span>Bundesdata FC</span>
      </div>
      <h1 className="auth-title">Log in</h1>
      <p className="auth-lead">PostgreSQL auth coming soon.</p>
      <Link className="auth-back" to="/">
        ← Back to home
      </Link>
    </div>
  );
}
