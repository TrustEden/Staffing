import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

function Login() {
  const navigate = useNavigate();
  const { login, loading, user, error } = useAuth();
  const [username, setUsername] = useState("superadmin");
  const [password, setPassword] = useState("ChangeMe123!");
  const [formError, setFormError] = useState(null);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError(null);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setFormError("Login failed. Check your credentials and try again.");
    }
  };

  return (
    <section className="page auth-page">
      <div className="card auth-card">
        <h2>Sign In</h2>
        <p className="muted">
          Demo credentials are prefilled. Create more accounts in the admin dashboard.
        </p>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {formError ? <p className="error-text">{formError}</p> : null}
          {error && !formError ? <p className="error-text">{error.message}</p> : null}
          <button type="submit" className="primary" disabled={loading}>
            {loading ? "Signing in�" : "Login"}
          </button>
        </form>
      </div>
    </section>
  );
}

export default Login;
