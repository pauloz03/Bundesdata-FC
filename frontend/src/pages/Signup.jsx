import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiBaseUrl } from "../lib/api.js";

function normalizeEmailClient(email) {
  return String(email ?? "").trim().toLowerCase();
}

export default function Signup() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const [verifyOpen, setVerifyOpen] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);

  useEffect(() => {
    if (!verifyOpen) return;
    function onKey(e) {
      if (e.key === "Escape") setVerifyOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [verifyOpen]);

  const handleSignup = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match");
      return;
    }

    try {
      setLoading(true);

      const res = await fetch(`${apiBaseUrl}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
          name: name.trim() || undefined,
        }),
      });

      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.message || `Sign up failed (${res.status})`);
      }

      setPendingEmail(normalizeEmailClient(email));
      setVerificationCode("");
      setVerifyOpen(true);
    } catch (err) {
      console.error(err);
      alert(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  async function handleConfirmVerification(e) {
    e.preventDefault();
    if (!verificationCode.trim()) {
      alert("Enter the code from your email.");
      return;
    }
    try {
      setConfirmLoading(true);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      try {
        const res = await fetch(`${apiBaseUrl}/auth/confirm-signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: pendingEmail,
            code: verificationCode.trim(),
          }),
          signal: controller.signal,
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(
            body.message || `Verification failed (${res.status})`
          );
        }
        setVerifyOpen(false);
        alert(body.message || "Email verified. You can log in.");
        navigate("/login");
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (err) {
      if (err?.name === "AbortError") {
        alert(
          "Verification timed out. Please check your connection and try again."
        );
        return;
      }
      console.error(err);
      alert(err.message || String(err));
    } finally {
      setConfirmLoading(false);
    }
  }

  async function handleResendCode() {
    try {
      setResendLoading(true);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      try {
        const res = await fetch(`${apiBaseUrl}/auth/resend-confirmation`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: pendingEmail }),
          signal: controller.signal,
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(body.message || `Could not resend (${res.status})`);
        }
        alert(body.message || "Check your email for a new code.");
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (err) {
      if (err?.name === "AbortError") {
        alert(
          "Resend timed out. Please check your connection and try again."
        );
        return;
      }
      console.error(err);
      alert(err.message || String(err));
    } finally {
      setResendLoading(false);
    }
  }

  function handleSkipVerification() {
    setVerifyOpen(false);
    navigate("/login");
  }

  return (
    <div className="auth-stack auth-stack--relative">
      <div className="auth-app-name">
        <img src="/bundes.jpg" alt="" className="auth-app-name__logo" />
        <span>Bundesdata FC</span>
      </div>
      <h1 className="auth-title">Sign up</h1>
      <p className="auth-lead">Create your analyst account</p>

      <form className="auth-form" onSubmit={handleSignup}>
        <label className="auth-field">
          <span className="auth-label">Name</span>
          <input
            type="text"
            name="name"
            placeholder="Jane Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

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
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>

      <p className="auth-footer">
        Already have an account? <Link to="/login">Log in</Link>
      </p>

      <Link className="auth-back" to="/">
        ← Back to home
      </Link>

      {verifyOpen ? (
        <div
          className="auth-modal-overlay"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setVerifyOpen(false);
          }}
        >
          <div
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="verify-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="verify-modal-title" className="auth-modal-title">
              Verify your email
            </h2>
            <p className="auth-modal-text">
              We sent a code to <strong>{pendingEmail}</strong>. Enter it below
              to confirm your account.
            </p>
            <form className="auth-form" onSubmit={handleConfirmVerification}>
              <label className="auth-field">
                <span className="auth-label">Verification code</span>
                <input
                  type="text"
                  name="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  autoFocus
                />
              </label>
              <button
                type="submit"
                className="auth-button auth-button--primary"
                disabled={confirmLoading}
              >
                {confirmLoading ? "Verifying…" : "Confirm email"}
              </button>
            </form>
            <div className="auth-modal-actions">
              <button
                type="button"
                className="auth-button auth-button--secondary auth-modal-btn"
                onClick={handleResendCode}
                disabled={resendLoading || confirmLoading}
              >
                {resendLoading ? "Sending…" : "Resend code"}
              </button>
              <button
                type="button"
                className="auth-modal-linkish"
                onClick={handleSkipVerification}
              >
                Skip — log in later
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
