import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { decodeJwtPayload } from "../lib/jwt.js";

export default function Dashboard() {
  const navigate = useNavigate();
  const [label, setLabel] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setError("You are not signed in.");
      return;
    }
    const payload = decodeJwtPayload(token);
    const label =
      payload?.email ||
      payload?.["cognito:username"] ||
      payload?.phone_number ||
      payload?.sub;
    setLabel(label || "Signed in");
  }, []);

  function handleSignOut() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  if (error) {
    return (
      <div className="auth-stack">
        <h1 className="auth-title">Dashboard</h1>
        <p className="auth-lead">{error}</p>
        <Link className="auth-button auth-button--primary" to="/login">
          Log in
        </Link>
        <Link className="auth-back" to="/">
          ← Back to home
        </Link>
      </div>
    );
  }

  return (
    <div className="auth-stack">
      <h1 className="auth-title">Dashboard</h1>
      <p className="auth-lead">
        Signed in as <strong>{label || "…"}</strong>
      </p>
      <p className="auth-lead" style={{ fontSize: 14, marginTop: -12 }}>
        Session uses the ID token returned after login (verified with the backend).
      </p>
      <button
        type="button"
        className="auth-button auth-button--secondary"
        onClick={handleSignOut}
      >
        Sign out
      </button>
      <Link className="auth-back" to="/">
        ← Back to home
      </Link>
    </div>
  );
}
