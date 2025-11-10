import { useState } from "react";
import PropTypes from "prop-types";
import dayjs from "dayjs";

function ShiftCalendar({
  shifts,
  onViewClaims,
  onCancelShift,
  claimsByShift,
  onApproveClaim,
  onDenyClaim,
  onClaimShift,
  claimedShiftIds,
  isStaffView = false
}) {
  const [currentMonth, setCurrentMonth] = useState(dayjs());

  const startOfMonth = currentMonth.startOf("month");
  const endOfMonth = currentMonth.endOf("month");
  const startDate = startOfMonth.startOf("week");
  const endDate = endOfMonth.endOf("week");

  const getShiftsForDate = (date) => {
    const dateStr = date.format("YYYY-MM-DD");
    return shifts.filter((shift) => shift.date === dateStr);
  };

  const getDayColor = (date) => {
    const dayShifts = getShiftsForDate(date);
    if (dayShifts.length === 0) return "";

    const hasOpen = dayShifts.some((s) => s.status === "open");
    const hasApproved = dayShifts.some((s) => s.status === "approved");
    const hasPending = dayShifts.some((s) => s.status === "pending");

    if (hasPending) return "pending-claims";
    if (hasOpen) return "needs-coverage";
    if (hasApproved) return "covered";
    return "";
  };

  const renderCalendar = () => {
    const weeks = [];
    let days = [];
    let day = startDate;

    while (day.isBefore(endDate, "day") || day.isSame(endDate, "day")) {
      for (let i = 0; i < 7; i++) {
        const currentDay = day; // Capture the current day value
        const currentDayStr = currentDay.format("YYYY-MM-DD"); // Capture the string
        const dayShifts = getShiftsForDate(currentDay);
        const colorClass = getDayColor(currentDay);
        const isCurrentMonth = currentDay.month() === currentMonth.month();

        days.push(
          <div
            key={currentDayStr}
            className={`calendar-day ${colorClass} ${!isCurrentMonth ? "other-month" : ""}`}
            onClick={() => dayShifts.length > 0 && setSelectedDate(currentDayStr)}
            style={{ cursor: dayShifts.length > 0 ? "pointer" : "default" }}
          >
            <div className="day-number">{currentDay.date()}</div>
            {dayShifts.length > 0 && (
              <div className="shift-count">{dayShifts.length} shift{dayShifts.length !== 1 ? "s" : ""}</div>
            )}
          </div>
        );
        day = day.add(1, "day");
      }
      weeks.push(
        <div key={`week-${weeks.length}`} className="calendar-week">
          {days}
        </div>
      );
      days = [];
    }
    return weeks;
  };

  const [selectedDate, setSelectedDate] = useState(null);

  const formatTime = (value) => (value ? value.slice(0, 5) : value);

  return (
    <div className="shift-calendar">
      <div className="calendar-header">
        <button type="button" onClick={() => setCurrentMonth(currentMonth.subtract(1, "month"))}>
          &lt; Prev
        </button>
        <h3>{currentMonth.format("MMMM YYYY")}</h3>
        <button type="button" onClick={() => setCurrentMonth(currentMonth.add(1, "month"))}>
          Next &gt;
        </button>
      </div>

      <div className="calendar-legend">
        <span className="legend-item">
          <span className="legend-color needs-coverage"></span> Needs Coverage
        </span>
        <span className="legend-item">
          <span className="legend-color pending-claims"></span> Pending Claims
        </span>
        <span className="legend-item">
          <span className="legend-color covered"></span> Covered
        </span>
      </div>

      <div className="calendar-weekdays">
        <div>Sun</div>
        <div>Mon</div>
        <div>Tue</div>
        <div>Wed</div>
        <div>Thu</div>
        <div>Fri</div>
        <div>Sat</div>
      </div>

      <div className="calendar-body">{renderCalendar()}</div>

      {selectedDate && (
        <>
          <div className="modal-overlay" onClick={() => setSelectedDate(null)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h4>Shifts for {dayjs(selectedDate).format("MMMM D, YYYY")}</h4>
              <button type="button" onClick={() => setSelectedDate(null)} className="close-button">
                &times;
              </button>
            </div>
            <div className="modal-body">
              {getShiftsForDate(dayjs(selectedDate)).length === 0 ? (
                <p className="muted">No shifts for this day.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Facility</th>
                      <th>Time</th>
                      <th>Role(s)</th>
                      <th>Status</th>
                      <th>Visibility</th>
                      <th>Notes</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getShiftsForDate(dayjs(selectedDate)).map((shift) => (
                        <tr key={shift.id}>
                          <td>
                            <strong>{shift.facility_name || "Unknown"}</strong>
                          </td>
                          <td>
                            {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
                          </td>
                          <td>
                            <strong>{shift.role_required}</strong>
                          </td>
                          <td>
                            <span className={`badge status-${shift.status}`}>{shift.status}</span>
                          </td>
                          <td>
                            <span className="badge">{shift.visibility}</span>
                          </td>
                          <td>{shift.notes || <span className="muted">—</span>}</td>
                          <td>
                            {isStaffView ? (
                              <button
                                type="button"
                                className="primary"
                                disabled={claimedShiftIds?.has(shift.id) || shift.status !== "open"}
                                onClick={() => onClaimShift(shift.id)}
                              >
                                {claimedShiftIds?.has(shift.id) ? "Claimed" : "Claim Shift"}
                              </button>
                            ) : (
                              <>
                                <div className="button-row">
                                  <button type="button" onClick={() => onViewClaims(shift.id)}>
                                    View Claims
                                  </button>
                                  {shift.status !== "cancelled" && (
                                    <button type="button" onClick={() => onCancelShift(shift.id)}>
                                      Cancel
                                    </button>
                                  )}
                                </div>
                                {claimsByShift && claimsByShift[shift.id] && (
                                  <div className="claims-panel">
                                    <h5>Claims</h5>
                                    <ul>
                                      {claimsByShift[shift.id].map((claim) => (
                                        <li key={claim.id}>
                                          <strong>{claim.user_name || "Unknown"}</strong> – <span className={`badge status-${claim.status}`}>{claim.status}</span>
                                          {claim.status === "pending" && (
                                            <span className="button-row">
                                              <button type="button" onClick={() => onApproveClaim(shift.id, claim.id)}>
                                                Approve
                                              </button>
                                              <button type="button" onClick={() => onDenyClaim(shift.id, claim.id)}>
                                                Deny
                                              </button>
                                            </span>
                                          )}
                                        </li>
                                      ))}
                                      {claimsByShift[shift.id].length === 0 && (
                                        <li className="muted">No claims yet.</li>
                                      )}
                                    </ul>
                                  </div>
                                )}
                              </>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

ShiftCalendar.propTypes = {
  shifts: PropTypes.array.isRequired,
  onViewClaims: PropTypes.func,
  onCancelShift: PropTypes.func,
  claimsByShift: PropTypes.object,
  onApproveClaim: PropTypes.func,
  onDenyClaim: PropTypes.func,
  onClaimShift: PropTypes.func,
  claimedShiftIds: PropTypes.object,
  isStaffView: PropTypes.bool,
};

export default ShiftCalendar;
