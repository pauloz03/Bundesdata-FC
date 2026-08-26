import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login } from "../lib/api.js";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/dashboard";
  const signedUp = Boolean(location.state?.signedUp);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }
    try {
      setLoading(true);
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-stack">
      <div className="auth-app-name">
        <img src="/bundes.jpg" alt="" className="auth-app-name__logo" />
        <span>Bundesdata FC</span>
      </div>
      <h1 className="auth-title">Log in</h1>
      <p className="auth-lead">Access your analytics dashboard</p>
      {signedUp ? (
        <p className="auth-success">Account created. You can log in now.</p>
      ) : null}

      <form className="auth-form" onSubmit={handleLogin}>
        {error ? <p className="auth-error">{error}</p> : null}

        <label className="auth-field">
          <span className="auth-label">Email</span>
          <input
            type="email"
            name="email"
            autoComplete="username"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="auth-field">
          <span className="auth-label">Password</span>
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button
          type="submit"
          className="auth-button auth-button--primary"
          disabled={loading}
        >
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>

      <p className="auth-footer">
        No account? <Link to="/signup">Sign up</Link>
      </p>
      <Link className="auth-back" to="/">
        ← Back to home
      </Link>
    </div>
  );
}
