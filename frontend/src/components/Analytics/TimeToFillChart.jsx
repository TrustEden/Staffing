import PropTypes from "prop-types";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function TimeToFillChart({ data, loading, error }) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Average Time to Fill</h3>
        </div>
        <div className="card-body" style={{ minHeight: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p className="muted">Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Average Time to Fill</h3>
        </div>
        <div className="card-body">
          <p className="error-text">Failed to load time to fill data: {error.message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Average Time to Fill</h3>
        </div>
        <div className="card-body" style={{ minHeight: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p className="muted">No data available for the selected date range</p>
        </div>
      </div>
    );
  }

  const avgTimeToFill = data.reduce((sum, item) => sum + item.avgHours, 0) / data.length;

  return (
    <div className="card">
      <div className="card-header">
        <h3>Average Time to Fill</h3>
        <p className="muted" style={{ margin: 0 }}>Hours from posting to approval by week</p>
      </div>
      <div className="card-body">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="week"
              stroke="#6b7280"
              style={{ fontSize: "0.875rem" }}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: "0.875rem" }}
              label={{ value: "Hours", angle: -90, position: "insideLeft", style: { textAnchor: "middle" } }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "0.5rem",
                boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)"
              }}
              labelStyle={{ fontWeight: 600, marginBottom: "0.25rem" }}
            />
            <Legend />
            <Bar
              dataKey="avgHours"
              fill="#2563eb"
              radius={[8, 8, 0, 0]}
              name="Avg Hours to Fill"
            />
          </BarChart>
        </ResponsiveContainer>
        <div className="grid two-column" style={{ marginTop: "1rem" }}>
          <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(37, 99, 235, 0.05)", borderRadius: "0.5rem" }}>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#2563eb" }}>
              {avgTimeToFill.toFixed(1)}h
            </div>
            <div className="muted" style={{ fontSize: "0.875rem" }}>Average Time to Fill</div>
          </div>
          <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(148, 163, 184, 0.05)", borderRadius: "0.5rem" }}>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#1f2937" }}>
              {data.reduce((sum, item) => sum + item.shiftCount, 0)}
            </div>
            <div className="muted" style={{ fontSize: "0.875rem" }}>Total Shifts Analyzed</div>
          </div>
        </div>
      </div>
    </div>
  );
}

TimeToFillChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      week: PropTypes.string.isRequired,
      avgHours: PropTypes.number.isRequired,
      shiftCount: PropTypes.number,
    })
  ),
  loading: PropTypes.bool,
  error: PropTypes.object,
};

TimeToFillChart.defaultProps = {
  data: [],
  loading: false,
  error: null,
};

export default TimeToFillChart;
