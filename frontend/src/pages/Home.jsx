import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="auth-stack">
      <div className="auth-app-name">
        <img src="/bundes.jpg" alt="" className="auth-app-name__logo" />
        <span>Bundesdata FC</span>
      </div>
      <h1 className="auth-title">Welcome</h1>
      <p className="auth-lead">Choose an option to continue.</p>
      <div className="auth-actions auth-actions--column">
        <Link className="auth-button auth-button--primary" to="/performance">
          View performance (local demo)
        </Link>
        <Link className="auth-button auth-button--secondary" to="/login">
          Log in
        </Link>
        <Link className="auth-button auth-button--secondary" to="/signup">
          Sign up
        </Link>
      </div>
    </div>
  )
}
