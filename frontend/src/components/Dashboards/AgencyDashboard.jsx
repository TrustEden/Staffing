import PropTypes from "prop-types";
import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import {
  addAgencyStaff,
  claimShift,
  fetchAgencies,
  fetchAgencyFacilities,
  fetchAgencyRelationships,
  fetchAgencyStaff,
  fetchFacilities,
  fetchMyClaims,
  fetchShifts,
  listNotifications,
  markAllNotificationsRead,
  markNotification,
  requestFacilityLink,
} from "../../services/backend";
import NotificationsPanel from "../Common/NotificationsPanel.jsx";
import ShiftCalendar from "../Common/ShiftCalendar.jsx";
import { useAuth } from "../../hooks/useAuth";

const formatTime = (value) => (value ? value.slice(0, 5) : value);;

function AgencyDashboard({ isAgencyStaff }) {
  const { user } = useAuth();
  const [agency, setAgency] = useState(null);
  const [staff, setStaff] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [myClaims, setMyClaims] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [staffForm, setStaffForm] = useState({
    name: "",
    username: "",
    email: "",
    password: "",
    phone: "",
    role: "agency_staff",
  });
  const [loading, setLoading] = useState(true);
  const [relationships, setRelationships] = useState([]);
  const [allFacilities, setAllFacilities] = useState([]);
  const [facilitySearchTerm, setFacilitySearchTerm] = useState("");
  const [linkMessage, setLinkMessage] = useState(null);

  const agencyId = user?.company_id;

  const loadData = async () => {
    if (!agencyId) return;
    setLoading(true);
    try {
      const [agenciesData, staffData, facilitiesData, shiftsData, claimsData, notificationsData, allFacilitiesData, relationshipsData] =
        await Promise.all([
          fetchAgencies(),
          isAgencyStaff ? Promise.resolve([]) : fetchAgencyStaff(agencyId),
          fetchAgencyFacilities(agencyId),
          fetchShifts(),
          fetchMyClaims(),
          listNotifications(),
          fetchFacilities(),
          fetchAgencyRelationships(agencyId).catch(() => []),
        ]);
      setAgency(agenciesData.find((item) => item.id === agencyId) ?? agenciesData[0]);
      if (!isAgencyStaff) {
        setStaff(staffData);
      }
      setFacilities(facilitiesData);
      setShifts(shiftsData);
      setMyClaims(claimsData);
      setNotifications(notificationsData);
      setAllFacilities(allFacilitiesData);
      setRelationships(relationshipsData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStaffSubmit = async (event) => {
    event.preventDefault();
    if (!agencyId) return;
    const created = await addAgencyStaff(agencyId, staffForm);
    setStaff((prev) => [...prev, created]);
    setStaffForm({ name: "", username: "", email: "", password: "", phone: "", role: "agency_staff" });
  };

  const handleClaimShift = async (shiftId) => {
    const result = await claimShift(shiftId);
    setMyClaims((prev) => [{ ...result.claim, shift_id: shiftId }, ...prev]);
    await loadData();
    if (result.warnings.length) {
      window.alert(result.warnings.join("\n"));
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

  const handleRequestFacilityLink = async (facilityDisplayId) => {
    if (!agencyId) return;
    try {
      const result = await requestFacilityLink(agencyId, facilityDisplayId);
      setLinkMessage(result.message || "Link request sent successfully");
      await loadData();
    } catch (error) {
      setLinkMessage(error.response?.data?.detail || "Failed to send link request");
    }
  };

  // Filter facilities by search term
  const filteredFacilities = useMemo(() => {
    if (!facilitySearchTerm) return allFacilities;
    const search = facilitySearchTerm.toLowerCase();
    return allFacilities.filter((facility) =>
      facility.name.toLowerCase().includes(search) ||
      facility.display_id.toLowerCase().includes(search)
    );
  }, [allFacilities, facilitySearchTerm]);

  // Get relationship status for each facility
  const getFacilityRelationshipStatus = (facilityId) => {
    const relationship = relationships.find(
      (rel) => rel.agency_id === agencyId && rel.facility_id === facilityId
    );
    return relationship?.status || "not_linked";
  };

  const claimedShiftIds = useMemo(() => new Set(myClaims.map((claim) => claim.shift_id)), [myClaims]);

  const facilityLookup = useMemo(() => {
    const map = new Map();
    facilities.forEach((facility) => {
      map.set(facility.id, facility.name);
    });
    return map;
  }, [facilities]);

  const enrichedShifts = useMemo(() => {
    return shifts.map((shift) => ({
      ...shift,
      facility_name: facilityLookup.get(shift.facility_id) ?? "Unknown Facility",
    }));
  }, [shifts, facilityLookup]);

  return (
    <section className="page dashboard">
      <header className="page-header">
        <h2>{isAgencyStaff ? "Agency Staff" : "Agency Admin"} Dashboard</h2>
        {agency ? (
          <p className="muted">
            Working with <strong>{agency.name}</strong>
          </p>
        ) : null}
      </header>

      {loading ? <div className="card">Loading agency data�</div> : null}

      {!isAgencyStaff ? (
        <section className="card">
          <h3>Add Agency Staff</h3>
          <form className="form" onSubmit={handleStaffSubmit}>
            <label>
              Name
              <input
                value={staffForm.name}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, name: event.target.value }))}
                required
              />
            </label>
            <label>
              Username
              <input
                type="text"
                value={staffForm.username}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, username: event.target.value }))}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={staffForm.password}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, password: event.target.value }))}
                required
                minLength={8}
              />
            </label>
            <label>
              Email (optional)
              <input
                type="email"
                value={staffForm.email}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, email: event.target.value }))}
              />
            </label>
            <label>
              Phone (optional)
              <input
                value={staffForm.phone}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, phone: event.target.value }))}
              />
            </label>
            <label>
              Role
              <select
                value={staffForm.role}
                onChange={(event) => setStaffForm((prev) => ({ ...prev, role: event.target.value }))}
              >
                <option value="agency_staff">Agency Staff</option>
                <option value="agency_admin">Agency Admin</option>
              </select>
            </label>
            <button type="submit" className="primary">
              Add Staff
            </button>
          </form>
        </section>
      ) : null}

      {!isAgencyStaff ? (
        <section className="card">
          <h3>Request Link to Facility</h3>
          <p className="muted" style={{ marginBottom: "1rem" }}>
            Request to connect with a facility. Requests must be approved by the platform admin.
          </p>
          {linkMessage && (
            <div className={`banner ${linkMessage.includes("success") || linkMessage.includes("sent") ? "success" : "error"}`}>
              {linkMessage}
            </div>
          )}
          <div style={{ marginBottom: "1rem" }}>
            <label>
              Search Facilities
              <input
                type="text"
                placeholder="Search by name or ID..."
                value={facilitySearchTerm}
                onChange={(e) => setFacilitySearchTerm(e.target.value)}
              />
            </label>
          </div>
          {filteredFacilities.length === 0 ? (
            <p className="muted">No facilities found.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Facility ID</th>
                  <th>Name</th>
                  <th>Address</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredFacilities.map((facility) => {
                  const status = getFacilityRelationshipStatus(facility.id);
                  return (
                    <tr key={facility.id}>
                      <td><strong style={{ color: "#2563eb" }}>{facility.display_id}</strong></td>
                      <td>{facility.name}</td>
                      <td>{facility.address || "—"}</td>
                      <td>
                        {status === "not_linked" && <span>Not Linked</span>}
                        {status === "invited" && <span className="badge status-invited">Pending Approval</span>}
                        {status === "active" && <span className="badge status-active">Active</span>}
                        {status === "revoked" && <span className="badge status-revoked">Revoked</span>}
                      </td>
                      <td>
                        {status === "not_linked" && (
                          <button
                            type="button"
                            className="primary"
                            onClick={() => handleRequestFacilityLink(facility.display_id)}
                          >
                            Request Link
                          </button>
                        )}
                        {status === "invited" && (
                          <button type="button" disabled>
                            Pending
                          </button>
                        )}
                        {status === "active" && (
                          <button type="button" disabled>
                            Linked
                          </button>
                        )}
                        {status === "revoked" && (
                          <button type="button" disabled title="Contact platform admin to restore">
                            Revoked
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ) : null}

      <div className="grid two-column">
        {!isAgencyStaff ? (
          <section className="card">
            <h3>Agency Team</h3>
            <ul className="list">
              {staff.map((member) => (
                <li key={member.id}>
                  <strong>{member.name}</strong> � {member.role}
                  <span className="muted">{member.email}</span>
                </li>
              ))}
              {staff.length === 0 ? <li className="muted">No staff added yet.</li> : null}
            </ul>
          </section>
        ) : null}

        <section className="card">
          <h3>Partner Facilities</h3>
          <ul className="list">
            {facilities.map((facility) => (
              <li key={facility.id}>
                <strong>{facility.name}</strong>
                <span className="muted">{facility.contact_email}</span>
              </li>
            ))}
            {facilities.length === 0 ? <li className="muted">No linked facilities yet.</li> : null}
          </ul>
        </section>
      </div>

      <section className="card">
        <h3>Available Shifts</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Facility</th>
              <th>Date</th>
              <th>Role</th>
              <th>Status</th>
              <th>Claim</th>
            </tr>
          </thead>
          <tbody>
            {shifts.map((shift) => (
              <tr key={shift.id}>
                <td>{facilityLookup.get(shift.facility_id) ?? shift.facility_id}</td>
                <td>
                  {dayjs(shift.date).format("MMM D, YYYY")} � {formatTime(shift.start_time)} � {formatTime(shift.end_time)}
                </td>
                <td>{shift.role_required}</td>
                <td>{shift.status}</td>
                <td>
                  <button
                    type="button"
                    disabled={claimedShiftIds.has(shift.id) || shift.status !== "open"}
                    onClick={() => handleClaimShift(shift.id)}
                  >
                    {claimedShiftIds.has(shift.id) ? "Claimed" : "Claim"}
                  </button>
                </td>
              </tr>
            ))}
            {shifts.length === 0 ? (
              <tr>
                <td colSpan={5} className="muted">
                  No shifts visible yet. Ensure relationships are active and visibility allows agency
                  access.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h3>Shift Calendar</h3>
        <ShiftCalendar
          shifts={enrichedShifts}
          isStaffView={true}
          onClaimShift={handleClaimShift}
          claimedShiftIds={claimedShiftIds}
        />
      </section>

      <section className="card">
        <h3>My Claims</h3>
        <ul className="list">
          {myClaims.map((claim) => (
            <li key={claim.id}>
              <div>
                <strong>{claim.shift_id}</strong> � {claim.status}
              </div>
              <span className="muted">{dayjs(claim.claimed_at).format("MMM D, YYYY h:mm A")}</span>
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

AgencyDashboard.propTypes = {
  isAgencyStaff: PropTypes.bool,
};

AgencyDashboard.defaultProps = {
  isAgencyStaff: false,
};

export default AgencyDashboard;
