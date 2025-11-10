import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import {
  addFacilityStaff,
  approveClaim,
  cancelShift,
  createShift,
  denyClaim,
  fetchAgencies,
  fetchFacilityRelationships,
  fetchFacilityStaff,
  fetchFacilities,
  fetchShiftClaims,
  fetchShifts,
  listNotifications,
  markAllNotificationsRead,
  markNotification,
  requestAgencyLink,
  uploadShifts,
} from "../../services/backend";
import NotificationsPanel from "../Common/NotificationsPanel.jsx";
import ShiftCalendar from "../Common/ShiftCalendar.jsx";
import { useAuth } from "../../hooks/useAuth";

const formatTime = (value) => (value ? value.slice(0, 5) : value);

const visibilityOptions = [
  { value: "internal", label: "Internal staff" },
  { value: "agency", label: "Agencies only" },
  { value: "all", label: "All" },
  { value: "tiered", label: "Tiered release" },
];

function FacilityAdminDashboard() {
  const { user } = useAuth();
  const [facility, setFacility] = useState(null);
  const [staff, setStaff] = useState([]);
  const [agencies, setAgencies] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [claimsByShift, setClaimsByShift] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [shiftForm, setShiftForm] = useState({
    date: "",
    start_time: "07:00",
    end_time: "15:00",
    roles: [],
    visibility: "internal",
    notes: "",
  });
  const [staffForm, setStaffForm] = useState({
    name: "",
    username: "",
    email: "",
    password: "",
    phone: "",
    role: "staff",
  });
  const [uploadMessage, setUploadMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [relationships, setRelationships] = useState([]);
  const [agencySearchTerm, setAgencySearchTerm] = useState("");
  const [linkMessage, setLinkMessage] = useState(null);

  const facilityId = user?.company_id;

  const loadData = async () => {
    if (!facilityId) return;
    setLoading(true);
    try {
      const [facilitiesData, staffData, agenciesData, shiftsData, notificationsData, relationshipsData] = await Promise.all([
        fetchFacilities(),
        fetchFacilityStaff(facilityId),
        fetchAgencies(),
        fetchShifts({ facility_id: facilityId }),
        listNotifications(),
        fetchFacilityRelationships(facilityId).catch(() => []),
      ]);
      setFacility(facilitiesData.find((item) => item.id === facilityId) ?? facilitiesData[0]);
      setStaff(staffData);
      setAgencies(agenciesData);
      setShifts(shiftsData);
      setNotifications(notificationsData);
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
    if (!facilityId) return;
    const created = await addFacilityStaff(facilityId, { ...staffForm });
    setStaff((prev) => [...prev, created]);
    setStaffForm({ name: "", username: "", email: "", password: "", phone: "", role: "staff" });
  };

  const handleShiftSubmit = async (event) => {
    event.preventDefault();
    if (!facilityId || shiftForm.roles.length === 0) return;

    // Create a single shift with comma-separated roles
    const payload = {
      facility_id: facilityId,
      date: shiftForm.date,
      start_time: shiftForm.start_time,
      end_time: shiftForm.end_time,
      role_required: shiftForm.roles.join(","), // Join roles with comma
      visibility: shiftForm.visibility,
      notes: shiftForm.notes,
    };
    const created = await createShift(payload);

    setShifts((prev) => [...prev, created]);
    setShiftForm({
      date: "",
      start_time: "07:00",
      end_time: "15:00",
      roles: [],
      visibility: shiftForm.visibility,
      notes: "",
    });
  };

  const handleCancelShift = async (shiftId) => {
    const cancelled = await cancelShift(shiftId);
    setShifts((prev) => prev.map((shift) => (shift.id === shiftId ? cancelled : shift)));
  };

  const handleViewClaims = async (shiftId) => {
    const claims = await fetchShiftClaims(shiftId);
    setClaimsByShift((prev) => ({ ...prev, [shiftId]: claims }));
  };

  const handleApproveClaim = async (shiftId, claimId) => {
    const approved = await approveClaim(shiftId, claimId);
    setClaimsByShift((prev) => ({
      ...prev,
      [shiftId]: (prev[shiftId] || []).map((claim) => (claim.id === claimId ? approved : claim)),
    }));
    await loadData();
  };

  const handleDenyClaim = async (shiftId, claimId) => {
    const reason = window.prompt("Why was this claim denied? (optional)") ?? "";
    const denied = await denyClaim(shiftId, claimId, reason);
    setClaimsByShift((prev) => ({
      ...prev,
      [shiftId]: (prev[shiftId] || []).map((claim) => (claim.id === claimId ? denied : claim)),
    }));
    await loadData();
  };

  const handleUpload = async (event) => {
    if (!facilityId) return;
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const createdShifts = await uploadShifts(facilityId, file);
      setShifts((prev) => [...prev, ...createdShifts]);
      setUploadMessage(`Uploaded ${createdShifts.length} shifts.`);
    } catch (error) {
      console.error(error);
      setUploadMessage("Upload failed. Check file format.");
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

  const handleRequestAgencyLink = async (agencyDisplayId) => {
    if (!facilityId) return;
    try {
      const result = await requestAgencyLink(facilityId, agencyDisplayId);
      setLinkMessage(result.message || "Link request sent successfully");
      await loadData();
    } catch (error) {
      setLinkMessage(error.response?.data?.detail || "Failed to send link request");
    }
  };

  // Filter agencies by search term
  const filteredAgencies = useMemo(() => {
    if (!agencySearchTerm) return agencies;
    const search = agencySearchTerm.toLowerCase();
    return agencies.filter((agency) =>
      agency.name.toLowerCase().includes(search) ||
      agency.display_id.toLowerCase().includes(search)
    );
  }, [agencies, agencySearchTerm]);

  // Get relationship status for each agency
  const getAgencyRelationshipStatus = (agencyId) => {
    const relationship = relationships.find(
      (rel) => rel.facility_id === facilityId && rel.agency_id === agencyId
    );
    return relationship?.status || "not_linked";
  };

  return (
    <section className="page dashboard">
      <header className="page-header">
        <h2>Facility Admin Dashboard</h2>
        {facility ? (
          <p className="muted">
            Managing <strong>{facility.name}</strong> ({facility.timezone})
          </p>
        ) : null}
      </header>

      {loading ? <div className="card">Loading facility data�</div> : null}

      <div className="grid two-column">
        <section className="card">
          <h3>Add Staff Member</h3>
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
                <option value="staff">Facility Staff</option>
                <option value="admin">Facility Admin</option>
              </select>
            </label>
            <button type="submit" className="primary">
              Add Staff Member
            </button>
          </form>
        </section>

        <section className="card">
          <h3>Create Shift</h3>
          <form className="form" onSubmit={handleShiftSubmit}>
            <label>
              Date
              <input
                type="date"
                value={shiftForm.date}
                onChange={(event) => setShiftForm((prev) => ({ ...prev, date: event.target.value }))}
                required
              />
            </label>
            <div className="grid two-column compact">
              <label>
                Start
                <input
                  type="time"
                  value={shiftForm.start_time}
                  onChange={(event) =>
                    setShiftForm((prev) => ({ ...prev, start_time: event.target.value }))
                  }
                  required
                />
              </label>
              <label>
                End
                <input
                  type="time"
                  value={shiftForm.end_time}
                  onChange={(event) =>
                    setShiftForm((prev) => ({ ...prev, end_time: event.target.value }))
                  }
                  required
                />
              </label>
            </div>
            <fieldset>
              <legend>Roles Required (select one or more)</legend>
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                {["RN", "LPN", "CMA", "CNA"].map((role) => (
                  <label key={role} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <input
                      type="checkbox"
                      checked={shiftForm.roles.includes(role)}
                      onChange={(event) => {
                        if (event.target.checked) {
                          setShiftForm((prev) => ({ ...prev, roles: [...prev.roles, role] }));
                        } else {
                          setShiftForm((prev) => ({
                            ...prev,
                            roles: prev.roles.filter((r) => r !== role),
                          }));
                        }
                      }}
                    />
                    {role}
                  </label>
                ))}
              </div>
            </fieldset>
            <label>
              Visibility
              <select
                value={shiftForm.visibility}
                onChange={(event) => setShiftForm((prev) => ({ ...prev, visibility: event.target.value }))}
              >
                {visibilityOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Notes
              <textarea
                value={shiftForm.notes}
                onChange={(event) => setShiftForm((prev) => ({ ...prev, notes: event.target.value }))}
              />
            </label>
            <button type="submit" className="primary">
              Publish Shift
            </button>
          </form>
        </section>
      </div>

      <section className="card">
        <h3>Request Link to Agency</h3>
        <p className="muted" style={{ marginBottom: "1rem" }}>
          Request to connect with an agency. Requests must be approved by the platform admin.
        </p>
        {linkMessage && (
          <div className={`banner ${linkMessage.includes("success") || linkMessage.includes("sent") ? "success" : "error"}`}>
            {linkMessage}
          </div>
        )}
        <div style={{ marginBottom: "1rem" }}>
          <label>
            Search Agencies
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={agencySearchTerm}
              onChange={(e) => setAgencySearchTerm(e.target.value)}
            />
          </label>
        </div>
        {filteredAgencies.length === 0 ? (
          <p className="muted">No agencies found.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Agency ID</th>
                <th>Name</th>
                <th>Address</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredAgencies.map((agency) => {
                const status = getAgencyRelationshipStatus(agency.id);
                return (
                  <tr key={agency.id}>
                    <td><strong style={{ color: "#059669" }}>{agency.display_id}</strong></td>
                    <td>{agency.name}</td>
                    <td>{agency.address || "—"}</td>
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
                          onClick={() => handleRequestAgencyLink(agency.display_id)}
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

      <section className="card">
        <header className="card-header">
          <h3>Upload Schedule</h3>
        </header>
        <div>
          <p className="muted" style={{ marginBottom: "0.75rem" }}>
            Upload multiple shifts at once using a CSV or Excel file.
          </p>
          <div style={{ marginBottom: "1rem", padding: "0.75rem", background: "rgba(148, 163, 184, 0.06)", borderRadius: "0.6rem" }}>
            <strong>Required Columns:</strong>
            <ul style={{ marginTop: "0.5rem", marginBottom: "0", paddingLeft: "1.5rem" }}>
              <li><strong>date</strong>: Shift date (YYYY-MM-DD format, e.g., 2025-11-01)</li>
              <li><strong>start_time</strong>: Start time (HH:MM format, e.g., 07:00)</li>
              <li><strong>end_time</strong>: End time (HH:MM format, e.g., 15:00)</li>
              <li><strong>role_required</strong>: Role needed (RN, LPN, CMA, or CNA)</li>
            </ul>
            <strong style={{ marginTop: "0.75rem", display: "block" }}>Optional Columns:</strong>
            <ul style={{ marginTop: "0.5rem", marginBottom: "0", paddingLeft: "1.5rem" }}>
              <li><strong>visibility</strong>: internal, agency, all, or tiered (defaults to internal)</li>
              <li><strong>notes</strong>: Additional shift notes</li>
            </ul>
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <a
              href="/docs/shift-upload-template.csv"
              download="shift-upload-template.csv"
              style={{ color: "var(--primary)", textDecoration: "underline", cursor: "pointer" }}
            >
              Download Template File
            </a>
          </div>
          <input type="file" accept=".csv,.xlsx,.xls" onChange={handleUpload} />
          {uploadMessage && <p className="muted" style={{ marginTop: "0.75rem" }}>{uploadMessage}</p>}
        </div>
      </section>

      <section className="card">
        <h3>Shift Calendar</h3>
        <ShiftCalendar
          shifts={shifts}
          onViewClaims={handleViewClaims}
          onCancelShift={handleCancelShift}
          claimsByShift={claimsByShift}
          onApproveClaim={handleApproveClaim}
          onDenyClaim={handleDenyClaim}
        />
      </section>

      <div className="grid two-column">
        <section className="card">
          <h3>Staff Roster</h3>
          <ul className="list">
            {staff.map((member) => (
              <li key={member.id}>
                <span>
                  <strong>{member.name}</strong> � {member.role}
                </span>
                <span className="muted">{member.email}</span>
              </li>
            ))}
            {staff.length === 0 ? <li className="muted">No staff yet.</li> : null}
          </ul>
        </section>

        <section className="card">
          <h3>Connected Agencies</h3>
          <ul className="list">
            {agencies.map((agency) => (
              <li key={agency.id}>
                <strong>{agency.name}</strong>
                <span className="muted">{agency.contact_email}</span>
              </li>
            ))}
            {agencies.length === 0 ? <li className="muted">No agencies linked yet.</li> : null}
          </ul>
        </section>
      </div>

      <NotificationsPanel
        notifications={notifications}
        onMarkRead={handleMarkNotification}
        onMarkAll={handleMarkAll}
      />
    </section>
  );
}

export default FacilityAdminDashboard;
