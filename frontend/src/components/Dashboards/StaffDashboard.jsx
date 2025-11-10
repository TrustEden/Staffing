import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import {
  claimShift,
  fetchMyClaims,
  fetchShifts,
  listNotifications,
  markAllNotificationsRead,
  markNotification,
} from "../../services/backend";
import NotificationsPanel from "../Common/NotificationsPanel.jsx";
import { useAuth } from "../../hooks/useAuth";
import ShiftCalendar from "../Common/ShiftCalendar.jsx";

const formatTime = (value) => (value ? value.slice(0, 5) : value);;

function StaffDashboard() {
  const { user } = useAuth();
  const [shifts, setShifts] = useState([]);
  const [myClaims, setMyClaims] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [shiftData, claimData, notificationData] = await Promise.all([
        fetchShifts(),
        fetchMyClaims(),
        listNotifications(),
      ]);
      console.log("Staff Dashboard - Loaded shifts:", shiftData);
      console.log("Staff Dashboard - Loaded claims:", claimData);
      setShifts(shiftData);
      setMyClaims(claimData);
      setNotifications(notificationData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleClaimShift = async (shiftId) => {
    const response = await claimShift(shiftId);
    setMyClaims((prev) => [{ ...response.claim, shift_id: shiftId }, ...prev]);
    await loadData();
    if (response.warnings.length) {
      window.alert(response.warnings.join("\n"));
    }
  };

  const handleMarkNotification = async (id, read) => {
    await markNotification(id, read);
    setNotifications((prev) => prev.map((note) => (note.id === id ? { ...note, read } : note)));
  };

  const handleMarkAll = async () => {
    await markAllNotificationsRead();
    setNotifications((prev) => prev.map((note) => ({ ...note, read: true })));
  };

  const claimedShiftIds = useMemo(() => new Set(myClaims.map((claim) => claim.shift_id)), [myClaims]);

  return (
    <section className="page dashboard">
      <header className="page-header">
        <h2>{user?.role === "agency_staff" ? "Agency Staff" : "Facility Staff"} Dashboard</h2>
        <p className="muted">Pick up available shifts and track your claim status.</p>
      </header>

      {loading ? <div className="card">Loading shifts�</div> : null}

      <section className="card">
        <h3>Available Shifts</h3>
        <ShiftCalendar
          shifts={shifts}
          onClaimShift={handleClaimShift}
          claimedShiftIds={claimedShiftIds}
          isStaffView={true}
        />
      </section>

      <section className="card">
        <h3>My Claims</h3>
        <ul className="list">
          {myClaims.map((claim) => (
            <li key={claim.id}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                <strong>
                  {claim.shift ?
                    `${dayjs(claim.shift.date).format("MMM D, YYYY")} ${formatTime(claim.shift.start_time)} - ${formatTime(claim.shift.end_time)}`
                    : "Unknown Shift"}
                </strong>
                <span className="badge">{claim.shift?.role_required || "N/A"}</span>
                <span className={`badge status-${claim.status}`}>{claim.status}</span>
              </div>
              <span className="muted">
                {claim.shift?.facility_name && `${claim.shift.facility_name} • `}
                Claimed {dayjs(claim.claimed_at).format("MMM D, YYYY h:mm A")}
              </span>
            </li>
          ))}
          {myClaims.length === 0 ? <li className="muted">No claims yet.</li> : null}
        </ul>
      </section>

      <NotificationsPanel
        notifications={notifications}
        onMarkRead={handleMarkNotification}
        onMarkAll={handleMarkAll}
      />
    </section>
  );
}

export default StaffDashboard;
