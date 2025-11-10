import PropTypes from "prop-types";

function ShiftStatsTable({ data, loading, error }) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Shift Statistics</h3>
        </div>
        <div className="card-body">
          <p className="muted">Loading statistics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Shift Statistics</h3>
        </div>
        <div className="card-body">
          <p className="error-text">Failed to load shift statistics: {error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Shift Statistics</h3>
        </div>
        <div className="card-body">
          <p className="muted">No data available</p>
        </div>
      </div>
    );
  }

  const { total = 0, byStatus = {}, byTier = {} } = data;

  // Calculate percentages for status
  const statusData = [
    { label: "Open", count: byStatus.open || 0, className: "status-open" },
    { label: "Claimed", count: byStatus.claimed || 0, className: "status-pending" },
    { label: "Approved", count: byStatus.approved || 0, className: "status-approved" },
    { label: "Cancelled", count: byStatus.cancelled || 0, className: "status-cancelled" },
  ];

  // Calculate percentages for tier
  const tierData = [
    { label: "Internal", count: byTier.internal || 0 },
    { label: "Tier 1", count: byTier.tier_1 || 0 },
    { label: "Tier 2", count: byTier.tier_2 || 0 },
  ];

  const calculatePercentage = (count) => {
    if (total === 0) return "0.0";
    return ((count / total) * 100).toFixed(1);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3>Shift Statistics</h3>
        <p className="muted" style={{ margin: 0 }}>Breakdown by status and tier</p>
      </div>
      <div className="card-body">
        {/* Total Shifts Summary */}
        <div style={{ textAlign: "center", padding: "1.5rem", background: "rgba(37, 99, 235, 0.05)", borderRadius: "0.5rem", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "2.5rem", fontWeight: 700, color: "#2563eb" }}>
            {total}
          </div>
          <div className="muted" style={{ fontSize: "1rem" }}>Total Shifts</div>
        </div>

        {/* By Status */}
        <div style={{ marginBottom: "1.5rem" }}>
          <h4 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", color: "#1f2937" }}>By Status</h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Count</th>
                <th style={{ textAlign: "right" }}>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {statusData.map((item) => (
                <tr key={item.label}>
                  <td>
                    <span className={`badge ${item.className}`}>{item.label}</span>
                  </td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>{item.count}</td>
                  <td style={{ textAlign: "right", color: "#6b7280" }}>
                    {calculatePercentage(item.count)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* By Tier */}
        <div>
          <h4 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", color: "#1f2937" }}>By Tier</h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th style={{ textAlign: "right" }}>Count</th>
                <th style={{ textAlign: "right" }}>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {tierData.map((item) => (
                <tr key={item.label}>
                  <td style={{ fontWeight: 600 }}>{item.label}</td>
                  <td style={{ textAlign: "right", fontWeight: 600 }}>{item.count}</td>
                  <td style={{ textAlign: "right", color: "#6b7280" }}>
                    {calculatePercentage(item.count)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

ShiftStatsTable.propTypes = {
  data: PropTypes.shape({
    total: PropTypes.number,
    byStatus: PropTypes.shape({
      open: PropTypes.number,
      claimed: PropTypes.number,
      approved: PropTypes.number,
      cancelled: PropTypes.number,
    }),
    byTier: PropTypes.shape({
      internal: PropTypes.number,
      tier_1: PropTypes.number,
      tier_2: PropTypes.number,
    }),
  }),
  loading: PropTypes.bool,
  error: PropTypes.object,
};

ShiftStatsTable.defaultProps = {
  data: null,
  loading: false,
  error: null,
};

export default ShiftStatsTable;
