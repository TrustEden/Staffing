import { useEffect, useState } from "react";
import { fetchCompanyStats, updateCompanyLockStatus, resetCompanyAdminPassword } from "../../services/backend";

function CompanyInfoModal({ company, onClose, onUpdate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newPassword, setNewPassword] = useState("");
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadStats();
  }, [company.id]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await fetchCompanyStats(company.id);
      setStats(data);
    } catch (error) {
      console.error("Failed to load company stats:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleLock = async () => {
    if (!stats) return;

    const confirmMessage = stats.is_locked
      ? `Are you sure you want to UNLOCK ${company.name}? This will reactivate all user accounts.`
      : `Are you sure you want to LOCK ${company.name}? This will deactivate all user accounts.`;

    if (!window.confirm(confirmMessage)) return;

    try {
      const result = await updateCompanyLockStatus(company.id, !stats.is_locked);
      setMessage(result.message);
      loadStats();
      if (onUpdate) onUpdate();
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handlePasswordReset = async (e) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      setMessage("Password must be at least 8 characters");
      return;
    }

    if (!window.confirm(`Reset admin password for ${company.name}?`)) return;

    try {
      const result = await resetCompanyAdminPassword(company.id, newPassword);
      setMessage(result.message);
      setNewPassword("");
      setShowPasswordReset(false);
    } catch (error) {
      setMessage(`Error: ${error.response?.data?.detail || error.message}`);
    }
  };

  if (!company) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            {company.name}
            <span style={{ fontSize: "0.875rem", marginLeft: "0.5rem", color: "#6b7280" }}>
              ({company.display_id})
            </span>
          </h2>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          {message && (
            <div className="banner info" style={{ marginBottom: "1rem" }}>
              {message}
            </div>
          )}

          {loading ? (
            <p>Loading statistics...</p>
          ) : stats ? (
            <>
              <div className="info-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
                <div className="info-item">
                  <label className="muted">Address</label>
                  <p>{company.address || "—"}</p>
                </div>
                <div className="info-item">
                  <label className="muted">Contact Email</label>
                  <p>{company.contact_email || "—"}</p>
                </div>
                <div className="info-item">
                  <label className="muted">Phone</label>
                  <p>{company.phone || "—"}</p>
                </div>
                <div className="info-item">
                  <label className="muted">Status</label>
                  <p>
                    <span className={`badge ${stats.is_locked ? "status-revoked" : "status-active"}`}>
                      {stats.is_locked ? "Locked" : "Active"}
                    </span>
                  </p>
                </div>
              </div>

              <h3 style={{ marginTop: "1.5rem", marginBottom: "0.75rem" }}>Statistics</h3>
              <div className="stats-grid" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
                <div className="stat-card" style={{ padding: "1rem", background: "#f3f4f6", borderRadius: "0.5rem" }}>
                  <div className="muted" style={{ fontSize: "0.875rem" }}>Employees</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "600", marginTop: "0.25rem" }}>
                    {stats.employee_count}
                  </div>
                </div>
                <div className="stat-card" style={{ padding: "1rem", background: "#f3f4f6", borderRadius: "0.5rem" }}>
                  <div className="muted" style={{ fontSize: "0.875rem" }}>Total Shifts</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "600", marginTop: "0.25rem" }}>
                    {stats.total_shifts}
                  </div>
                </div>
                <div className="stat-card" style={{ padding: "1rem", background: "#f3f4f6", borderRadius: "0.5rem" }}>
                  <div className="muted" style={{ fontSize: "0.875rem" }}>Fill Rate</div>
                  <div style={{ fontSize: "1.5rem", fontWeight: "600", marginTop: "0.25rem", color: stats.fill_rate > 80 ? "#059669" : stats.fill_rate > 50 ? "#f59e0b" : "#dc2626" }}>
                    {stats.fill_rate}%
                  </div>
                  <div className="muted" style={{ fontSize: "0.75rem" }}>
                    {stats.filled_shifts} / {stats.total_shifts}
                  </div>
                </div>
              </div>

              <h3 style={{ marginTop: "1.5rem", marginBottom: "0.75rem" }}>Admin Actions</h3>
              <div className="action-buttons" style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  onClick={handleToggleLock}
                  className={stats.is_locked ? "primary" : ""}
                  style={{ flex: "1 1 auto" }}
                >
                  {stats.is_locked ? "🔓 Unlock Account" : "🔒 Lock Account"}
                </button>

                {!showPasswordReset ? (
                  <button
                    onClick={() => setShowPasswordReset(true)}
                    style={{ flex: "1 1 auto" }}
                  >
                    🔑 Reset Admin Password
                  </button>
                ) : (
                  <form
                    onSubmit={handlePasswordReset}
                    style={{ display: "flex", gap: "0.5rem", flex: "1 1 100%", alignItems: "flex-end" }}
                  >
                    <label style={{ flex: 1 }}>
                      New Password
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        minLength={8}
                        required
                        placeholder="Minimum 8 characters"
                      />
                    </label>
                    <button type="submit" className="primary">
                      Reset
                    </button>
                    <button type="button" onClick={() => {
                      setShowPasswordReset(false);
                      setNewPassword("");
                    }}>
                      Cancel
                    </button>
                  </form>
                )}
              </div>
            </>
          ) : (
            <p className="muted">Failed to load statistics</p>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default CompanyInfoModal;
