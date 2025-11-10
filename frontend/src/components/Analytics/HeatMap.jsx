import PropTypes from "prop-types";
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, parseISO } from "date-fns";

function HeatMap({ data, loading, error, currentDate }) {
  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Shift Density Heat Map</h3>
        </div>
        <div className="card-body" style={{ minHeight: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p className="muted">Loading heat map...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3>Shift Density Heat Map</h3>
        </div>
        <div className="card-body">
          <p className="error-text">Failed to load heat map data: {error.message}</p>
        </div>
      </div>
    );
  }

  // Create a map of date to shift count
  const shiftMap = {};
  if (data && data.length > 0) {
    data.forEach((item) => {
      shiftMap[item.date] = item.count;
    });
  }

  // Get the max count for color scaling
  const maxCount = data && data.length > 0 ? Math.max(...data.map(d => d.count)) : 0;

  // Get intensity color based on count
  const getIntensityColor = (count) => {
    if (!count || count === 0) return "#f8fafc";
    const intensity = count / maxCount;
    if (intensity >= 0.75) return "#1d4ed8"; // Very high
    if (intensity >= 0.5) return "#3b82f6"; // High
    if (intensity >= 0.25) return "#93c5fd"; // Medium
    return "#dbeafe"; // Low
  };

  const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Generate calendar days
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);

  // Get all days in the current view (including days from prev/next month to fill weeks)
  const startDate = new Date(monthStart);
  startDate.setDate(startDate.getDate() - startDate.getDay());

  const endDate = new Date(monthEnd);
  endDate.setDate(endDate.getDate() + (6 - endDate.getDay()));

  const allDays = eachDayOfInterval({ start: startDate, end: endDate });

  // Group days into weeks
  const weeks = [];
  for (let i = 0; i < allDays.length; i += 7) {
    weeks.push(allDays.slice(i, i + 7));
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3>Shift Density Heat Map</h3>
        <p className="muted" style={{ margin: 0 }}>Daily shift volume visualization</p>
      </div>
      <div className="card-body">
        {/* Legend */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem", padding: "0.75rem", background: "rgba(148, 163, 184, 0.06)", borderRadius: "0.5rem" }}>
          <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>Intensity:</span>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <div style={{ width: "20px", height: "20px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "4px" }}></div>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>None</span>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <div style={{ width: "20px", height: "20px", background: "#dbeafe", border: "1px solid #e2e8f0", borderRadius: "4px" }}></div>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Low</span>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <div style={{ width: "20px", height: "20px", background: "#93c5fd", border: "1px solid #e2e8f0", borderRadius: "4px" }}></div>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Medium</span>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <div style={{ width: "20px", height: "20px", background: "#3b82f6", border: "1px solid #e2e8f0", borderRadius: "4px" }}></div>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>High</span>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <div style={{ width: "20px", height: "20px", background: "#1d4ed8", border: "1px solid #e2e8f0", borderRadius: "4px" }}></div>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>Very High</span>
          </div>
        </div>

        {/* Calendar Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: "0.5rem",
          marginBottom: "0.5rem",
          fontWeight: 600,
          fontSize: "0.875rem",
          color: "#6b7280",
          textAlign: "center"
        }}>
          {weekDays.map(day => (
            <div key={day}>{day}</div>
          ))}
        </div>

        {/* Calendar Body */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {weeks.map((week, weekIdx) => (
            <div
              key={weekIdx}
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                gap: "0.5rem"
              }}
            >
              {week.map((day) => {
                const dateStr = format(day, "yyyy-MM-dd");
                const count = shiftMap[dateStr] || 0;
                const isCurrentMonth = isSameMonth(day, currentDate);
                const bgColor = getIntensityColor(count);

                return (
                  <div
                    key={dateStr}
                    style={{
                      minHeight: "60px",
                      padding: "0.5rem",
                      background: bgColor,
                      border: "1px solid #e2e8f0",
                      borderRadius: "0.5rem",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "0.25rem",
                      opacity: isCurrentMonth ? 1 : 0.4,
                      transition: "all 0.2s ease",
                      cursor: count > 0 ? "pointer" : "default",
                    }}
                    title={count > 0 ? `${count} shift${count !== 1 ? 's' : ''}` : "No shifts"}
                  >
                    <div style={{ fontWeight: 600, fontSize: "1rem" }}>{format(day, "d")}</div>
                    {count > 0 && (
                      <div style={{
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        color: count > maxCount * 0.5 ? "#ffffff" : "#1f2937"
                      }}>
                        {count}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Summary Stats */}
        {data && data.length > 0 && (
          <div className="grid two-column" style={{ marginTop: "1.5rem" }}>
            <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(37, 99, 235, 0.05)", borderRadius: "0.5rem" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#2563eb" }}>
                {data.reduce((sum, item) => sum + item.count, 0)}
              </div>
              <div className="muted" style={{ fontSize: "0.875rem" }}>Total Shifts</div>
            </div>
            <div style={{ textAlign: "center", padding: "0.75rem", background: "rgba(148, 163, 184, 0.05)", borderRadius: "0.5rem" }}>
              <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "#1f2937" }}>
                {maxCount}
              </div>
              <div className="muted" style={{ fontSize: "0.875rem" }}>Peak Day Volume</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

HeatMap.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      date: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired,
    })
  ),
  loading: PropTypes.bool,
  error: PropTypes.object,
  currentDate: PropTypes.instanceOf(Date),
};

HeatMap.defaultProps = {
  data: [],
  loading: false,
  error: null,
  currentDate: new Date(),
};

export default HeatMap;
