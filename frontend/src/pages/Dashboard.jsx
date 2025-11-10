import { useAuth } from "../hooks/useAuth";
import AgencyDashboard from "../components/Dashboards/AgencyDashboard.jsx";
import FacilityAdminDashboard from "../components/Dashboards/FacilityAdminDashboard.jsx";
import StaffDashboard from "../components/Dashboards/StaffDashboard.jsx";
import SuperAdminDashboard from "../components/Dashboards/SuperAdminDashboard.jsx";

function Dashboard() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="page-loading">Loading dashboard…</div>;
  }

  if (!user) {
    return null;
  }

  if (user.role === "admin" && !user.company_id) {
    return <SuperAdminDashboard />;
  }

  if (user.role === "admin" && user.company_id) {
    return <FacilityAdminDashboard />;
  }

  if (user.role === "agency_admin") {
    return <AgencyDashboard isAgencyStaff={false} />;
  }

  if (user.role === "agency_staff") {
    return <AgencyDashboard isAgencyStaff />;
  }

  if (user.role === "staff") {
    return <StaffDashboard />;
  }

  return (
    <section className="page">
      <h2>Unsupported role</h2>
      <p>
        This account role does not yet have a dashboard in the demo. Please log in with another
        user.
      </p>
    </section>
  );
}

export default Dashboard;
