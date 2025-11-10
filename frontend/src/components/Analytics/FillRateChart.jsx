import PropTypes from "prop-types";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

function FillRateChart({ data, loading, error }) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Fill Rate Over Time</h3>
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
          <h3>Fill Rate Over Time</h3>
        </div>
        <div className="card-body">
          <p className="error-text">Failed to load fill rate data: {error.message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Fill Rate Over Time</h3>
        </div>
        <div className="card-body" style={{ minHeight: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p className="muted">No data available for the selected date range</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3>Fill Rate Over Time</h3>
        <p className="muted" style={{ margin: 0 }}>Percentage of shifts filled vs. total shifts</p>
      </div>
      <div className="card-body">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              stroke="#6b7280"
              style={{ fontSize: "0.875rem" }}
            />
            <YAxis
              stroke="#6b7280"
              style={{ fontSize: "0.875rem" }}
              label={{ value: "Fill Rate (%)", angle: -90, position: "insideLeft", style: { textAnchor: "middle" } }}
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
            <Line
              type="monotone"
              dataKey="fillRate"
              stroke="#2563eb"
              strokeWidth={2}
              dot={{ fill: "#2563eb", r: 4 }}
              activeDot={{ r: 6 }}
              name="Fill Rate (%)"
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="grid two-column" style={{ marginTop: "1rem" }}>
          <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(37, 99, 235, 0.05)", borderRadius: "0.5rem" }}>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#2563eb" }}>
              {data.length > 0 ? `${data[data.length - 1].fillRate.toFixed(1)}%` : "N/A"}
            </div>
            <div className="muted" style={{ fontSize: "0.875rem" }}>Current Fill Rate</div>
          </div>
          <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(148, 163, 184, 0.05)", borderRadius: "0.5rem" }}>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#1f2937" }}>
              {data.reduce((sum, item) => sum + item.fillRate, 0) / data.length > 0
                ? (data.reduce((sum, item) => sum + item.fillRate, 0) / data.length).toFixed(1)
                : "0"}%
            </div>
            <div className="muted" style={{ fontSize: "0.875rem" }}>Average Fill Rate</div>
          </div>
        </div>
      </div>
    </div>
  );
}

FillRateChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      date: PropTypes.string.isRequired,
      fillRate: PropTypes.number.isRequired,
      totalShifts: PropTypes.number,
      filledShifts: PropTypes.number,
    })
  ),
  loading: PropTypes.bool,
  error: PropTypes.object,
};

FillRateChart.defaultProps = {
  data: [],
  loading: false,
  error: null,
};

export default FillRateChart;
