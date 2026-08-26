import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup } from "../lib/api.js";

export default function Signup() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSignup(e) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    try {
      setLoading(true);
      await signup({ email, password });
      navigate("/login", { replace: true, state: { signedUp: true } });
    } catch (err) {
      setError(err.message || "Sign up failed");
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
      <h1 className="auth-title">Sign up</h1>
      <p className="auth-lead">Create an account to open the dashboard</p>

      <form className="auth-form" onSubmit={handleSignup}>
        {error ? <p className="auth-error">{error}</p> : null}

        <label className="auth-field">
          <span className="auth-label">Email</span>
          <input
            type="email"
            name="email"
            autoComplete="email"
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
            autoComplete="new-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <label className="auth-field">
          <span className="auth-label">Confirm password</span>
          <input
            type="password"
            name="confirmPassword"
            autoComplete="new-password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </label>

        <button
          type="submit"
          className="auth-button auth-button--primary"
          disabled={loading}
        >
          {loading ? "Creating account..." : "Sign up"}
        </button>
      </form>

      <p className="auth-footer">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
      <Link className="auth-back" to="/">
        ← Back to home
      </Link>
    </div>
  );
}
