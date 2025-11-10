import PropTypes from "prop-types";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

function AppLayout({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const isFacilityAdmin = user?.role === "admin" && user?.company_id;

  const links = user
    ? [
        { label: "Home", to: "/" },
        { label: "Dashboard", to: "/dashboard" },
        ...(isFacilityAdmin ? [{ label: "Analytics", to: "/analytics" }] : []),
      ]
    : [
        { label: "Home", to: "/" },
        { label: "Login", to: "/login" },
      ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-brand">
          <h1>Healthcare Staffing Bridge</h1>
          {user ? <span className="app-user">Signed in as {user.name}</span> : null}
        </div>
        <nav className="app-nav">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={location.pathname.startsWith(link.to) ? "active" : ""}
            >
              {link.label}
            </Link>
          ))}
          {user ? (
            <button type="button" className="link-button" onClick={handleLogout}>
              Logout
            </button>
          ) : null}
        </nav>
      </header>
      <main className="app-content">{children}</main>
    </div>
  );
}

AppLayout.propTypes = {
  children: PropTypes.node.isRequired,
};

export default AppLayout;
