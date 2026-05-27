import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiBaseUrl } from "../lib/api.js";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      setLoading(true);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      try {
        const loginRes = await fetch(`${apiBaseUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password }),
          signal: controller.signal,
        });

        const loginBody = await loginRes.json().catch(() => ({}));
        if (!loginRes.ok) {
          throw new Error(
            loginBody.message || `Login failed (${loginRes.status})`
          );
        }

        const idToken = loginBody.idToken;
        if (!idToken) {
          throw new Error("Server did not return an ID token.");
        }

        const protectedRes = await fetch(`${apiBaseUrl}/protected`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
          signal: controller.signal,
        });

        if (!protectedRes.ok) {
          const body = await protectedRes.json().catch(() => ({}));
          throw new Error(
            body.message ||
              `Backend verification failed (${protectedRes.status})`
          );
        }

        localStorage.setItem("token", idToken);
        navigate("/performance");
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (err) {
      if (err?.name === "AbortError") {
        alert(
          "Login timed out. Please check your connection and try again."
        );
        return;
      }

      console.error(err);
      alert(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-stack">
      <h1 className="auth-title">Log in</h1>
      <p className="auth-lead">Access your analytics dashboard</p>

      <form className="auth-form" onSubmit={handleLogin}>
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
