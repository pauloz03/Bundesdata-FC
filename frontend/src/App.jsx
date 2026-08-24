import { Navigate, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Performance from "./pages/Performance";
import AppLayout from "./components/AppLayout";
import "./App.css";

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <div className="auth-shell">
            <Home />
          </div>
        }
      />
      <Route
        path="/login"
        element={
          <div className="auth-shell">
            <Login />
          </div>
        }
      />
      <Route
        path="/signup"
        element={
          <div className="auth-shell">
            <Signup />
          </div>
        }
      />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/performance" element={<Performance />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
