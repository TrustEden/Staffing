import PropTypes from "prop-types";
import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./components/Common/AppLayout.jsx";
import { useAuth } from "./hooks/useAuth";
import Analytics from "./pages/Analytics.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="page-loading">Loading profile�</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

RequireAuth.propTypes = {
  children: PropTypes.node.isRequired,
};

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={(
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          )}
        />
        <Route
          path="/analytics"
          element={(
            <RequireAuth>
              <Analytics />
            </RequireAuth>
          )}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
