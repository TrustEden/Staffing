import { useState, useEffect } from "react";
import { format, subDays } from "date-fns";

import { useAuth } from "../hooks/useAuth";
import { getFillRate, getTimeToFill, getShiftStats, getShiftDensity } from "../services/analytics";
import FillRateChart from "../components/Analytics/FillRateChart";
import TimeToFillChart from "../components/Analytics/TimeToFillChart";
import ShiftStatsTable from "../components/Analytics/ShiftStatsTable";
import HeatMap from "../components/Analytics/HeatMap";
import ExportButton from "../components/Analytics/ExportButton";

function Analytics() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");

  // Date range state (default: last 30 days)
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(format(new Date(), "yyyy-MM-dd"));

  // Data states
  const [fillRateData, setFillRateData] = useState([]);
  const [timeToFillData, setTimeToFillData] = useState([]);
  const [shiftStatsData, setShiftStatsData] = useState(null);
  const [heatMapData, setHeatMapData] = useState([]);

  // Loading states
  const [fillRateLoading, setFillRateLoading] = useState(false);
  const [timeToFillLoading, setTimeToFillLoading] = useState(false);
  const [shiftStatsLoading, setShiftStatsLoading] = useState(false);
  const [heatMapLoading, setHeatMapLoading] = useState(false);

  // Error states
  const [fillRateError, setFillRateError] = useState(null);
  const [timeToFillError, setTimeToFillError] = useState(null);
  const [shiftStatsError, setShiftStatsError] = useState(null);
  const [heatMapError, setHeatMapError] = useState(null);

  const facilityId = user?.company_id;

  // Fetch all analytics data
  const fetchAnalytics = async () => {
    if (!facilityId) return;

    // Fetch fill rate data
    setFillRateLoading(true);
    setFillRateError(null);
    try {
      const data = await getFillRate(facilityId, startDate, endDate);
      setFillRateData(data);
    } catch (error) {
      setFillRateError(error);
      setFillRateData([]);
    } finally {
      setFillRateLoading(false);
    }

    // Fetch time to fill data
    setTimeToFillLoading(true);
    setTimeToFillError(null);
    try {
      const data = await getTimeToFill(facilityId, startDate, endDate);
      setTimeToFillData(data);
    } catch (error) {
      setTimeToFillError(error);
      setTimeToFillData([]);
    } finally {
      setTimeToFillLoading(false);
    }

    // Fetch shift stats
    setShiftStatsLoading(true);
    setShiftStatsError(null);
    try {
      const data = await getShiftStats(facilityId, startDate, endDate);
      setShiftStatsData(data);
    } catch (error) {
      setShiftStatsError(error);
      setShiftStatsData(null);
    } finally {
      setShiftStatsLoading(false);
    }

    // Fetch heat map data
    setHeatMapLoading(true);
    setHeatMapError(null);
    try {
      const data = await getShiftDensity(facilityId, startDate, endDate);
      setHeatMapData(data);
    } catch (error) {
      setHeatMapError(error);
      setHeatMapData([]);
    } finally {
      setHeatMapLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [startDate, endDate, facilityId]);

  const handleDateRangeChange = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const newStartDate = formData.get("start_date");
    const newEndDate = formData.get("end_date");

    if (newStartDate && newEndDate) {
      setStartDate(newStartDate);
      setEndDate(newEndDate);
    }
  };

  const setQuickRange = (days) => {
    setEndDate(format(new Date(), "yyyy-MM-dd"));
    setStartDate(format(subDays(new Date(), days), "yyyy-MM-dd"));
  };

  // Prepare CSV export data based on active tab
  const getExportData = () => {
    switch (activeTab) {
      case "overview":
        return fillRateData;
      case "time-to-fill":
        return timeToFillData;
      case "heatmap":
        return heatMapData;
      default:
        return [];
    }
  };

  return (
    <section className="page">
      <div className="page-header">
        <h2>Analytics Dashboard</h2>
        <p className="muted">Comprehensive insights into shift management and staffing performance</p>
      </div>

      {/* Date Range Filter */}
      <div className="card">
        <form onSubmit={handleDateRangeChange} className="form inline">
          <label>
            <span>Start Date</span>
            <input
              type="date"
              name="start_date"
              defaultValue={startDate}
              max={endDate}
            />
          </label>
          <label>
            <span>End Date</span>
            <input
              type="date"
              name="end_date"
              defaultValue={endDate}
              min={startDate}
              max={format(new Date(), "yyyy-MM-dd")}
            />
          </label>
          <button type="submit" className="primary">Apply</button>
          <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}>
            <button type="button" onClick={() => setQuickRange(7)}>Last 7 Days</button>
            <button type="button" onClick={() => setQuickRange(30)}>Last 30 Days</button>
            <button type="button" onClick={() => setQuickRange(90)}>Last 90 Days</button>
          </div>
        </form>
      </div>

      {/* Tab Navigation */}
      <div className="card">
        <div style={{
          display: "flex",
          gap: "0.5rem",
          borderBottom: "1px solid var(--border)",
          padding: "0 0 0.5rem 0"
        }}>
          <button
            onClick={() => setActiveTab("overview")}
            style={{
              background: activeTab === "overview" ? "rgba(37, 99, 235, 0.12)" : "transparent",
              color: activeTab === "overview" ? "var(--primary)" : "var(--text-muted)",
              fontWeight: activeTab === "overview" ? 600 : 400,
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem 0.5rem 0 0",
            }}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab("time-to-fill")}
            style={{
              background: activeTab === "time-to-fill" ? "rgba(37, 99, 235, 0.12)" : "transparent",
              color: activeTab === "time-to-fill" ? "var(--primary)" : "var(--text-muted)",
              fontWeight: activeTab === "time-to-fill" ? 600 : 400,
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem 0.5rem 0 0",
            }}
          >
            Time to Fill
          </button>
          <button
            onClick={() => setActiveTab("statistics")}
            style={{
              background: activeTab === "statistics" ? "rgba(37, 99, 235, 0.12)" : "transparent",
              color: activeTab === "statistics" ? "var(--primary)" : "var(--text-muted)",
              fontWeight: activeTab === "statistics" ? 600 : 400,
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem 0.5rem 0 0",
            }}
          >
            Statistics
          </button>
          <button
            onClick={() => setActiveTab("heatmap")}
            style={{
              background: activeTab === "heatmap" ? "rgba(37, 99, 235, 0.12)" : "transparent",
              color: activeTab === "heatmap" ? "var(--primary)" : "var(--text-muted)",
              fontWeight: activeTab === "heatmap" ? 600 : 400,
              padding: "0.5rem 1rem",
              borderRadius: "0.5rem 0.5rem 0 0",
            }}
          >
            Heat Map
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div id="analytics-content">
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <ExportButton
                type="csv"
                data={getExportData()}
                filename={`fill-rate-${startDate}-to-${endDate}`}
              />
              <ExportButton
                type="pdf"
                elementId="analytics-content"
                filename={`analytics-overview-${startDate}-to-${endDate}`}
              />
            </div>
            <FillRateChart data={fillRateData} loading={fillRateLoading} error={fillRateError} />
            <div className="grid two-column">
              <ShiftStatsTable data={shiftStatsData} loading={shiftStatsLoading} error={shiftStatsError} />
            </div>
          </div>
        )}

        {activeTab === "time-to-fill" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <ExportButton
                type="csv"
                data={getExportData()}
                filename={`time-to-fill-${startDate}-to-${endDate}`}
              />
              <ExportButton
                type="pdf"
                elementId="analytics-content"
                filename={`time-to-fill-${startDate}-to-${endDate}`}
              />
            </div>
            <TimeToFillChart data={timeToFillData} loading={timeToFillLoading} error={timeToFillError} />
          </div>
        )}

        {activeTab === "statistics" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <ExportButton
                type="pdf"
                elementId="analytics-content"
                filename={`shift-statistics-${startDate}-to-${endDate}`}
              />
            </div>
            <ShiftStatsTable data={shiftStatsData} loading={shiftStatsLoading} error={shiftStatsError} />
          </div>
        )}

        {activeTab === "heatmap" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <ExportButton
                type="csv"
                data={getExportData()}
                filename={`shift-density-${startDate}-to-${endDate}`}
              />
              <ExportButton
                type="pdf"
                elementId="analytics-content"
                filename={`shift-heatmap-${startDate}-to-${endDate}`}
              />
            </div>
            <HeatMap
              data={heatMapData}
              loading={heatMapLoading}
              error={heatMapError}
              currentDate={new Date()}
            />
          </div>
        )}
      </div>
    </section>
  );
}

export default Analytics;
