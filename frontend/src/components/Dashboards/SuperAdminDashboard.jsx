import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

import {
  createRelationship,
  fetchAgencies,
  fetchFacilities,
  listRelationships,
  updateRelationshipStatus,
  fetchPendingClaims,
} from "../../services/backend";
import CompanyInfoModal from "../Modals/CompanyInfoModal";
import AddCompanyModal from "../Modals/AddCompanyModal";

const timezones = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
];

function SuperAdminDashboard() {
  const [facilities, setFacilities] = useState([]);
  const [agencies, setAgencies] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [pendingClaims, setPendingClaims] = useState([]);
  const [relationshipForm, setRelationshipForm] = useState({
    facility_id: "",
    agency_id: "",
  });
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedCompanyForLinks, setSelectedCompanyForLinks] = useState(null);
  const [showAddCompanyModal, setShowAddCompanyModal] = useState(false);
  const [confirmationAction, setConfirmationAction] = useState(null); // { action: 'activate' | 'revoke', relationshipId, relationship }

  const loadData = async () => {
    setLoading(true);
    try {
      const [fac, ag, rel, pending] = await Promise.all([
        fetchFacilities(),
        fetchAgencies(),
        listRelationships(),
        fetchPendingClaims().catch(() => []),
      ]);
      setFacilities(fac);
      setAgencies(ag);
      setRelationships(rel);
      setPendingClaims(pending);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCompanyCreated = (created) => {
    if (created.type === "facility") {
      setFacilities((prev) => [...prev, created]);
    } else {
      setAgencies((prev) => [...prev, created]);
    }
    setMessage(`Created ${created.type} ${created.name} (${created.display_id}) with admin account.`);
  };

  const handleRelationshipSubmit = async (event) => {
    event.preventDefault();
    if (!relationshipForm.facility_id || !relationshipForm.agency_id) return;
    const created = await createRelationship(relationshipForm);
    setRelationships((prev) => [created, ...prev]);
    setRelationshipForm({ facility_id: "", agency_id: "" });
  };

  const showConfirmation = (action, relationshipId, relationship) => {
    setConfirmationAction({ action, relationshipId, relationship });
  };

  const cancelConfirmation = () => {
    setConfirmationAction(null);
  };

  const executeAction = async () => {
    if (!confirmationAction) return;

    const { action, relationshipId } = confirmationAction;
    try {
      const newStatus = action === "activate" ? "active" : "revoked";
      const updated = await updateRelationshipStatus(relationshipId, newStatus);
      setRelationships((prev) => prev.map((item) => (item.id === relationshipId ? updated : item)));

      let successMessage = "";
      if (action === "activate") {
        successMessage = "Successfully activated the relationship.";
      } else if (action === "unlink") {
        successMessage = "Successfully unlinked the companies.";
      } else {
        successMessage = "Successfully revoked the relationship.";
      }
      setMessage(successMessage);
    } catch (error) {
      setMessage(`Failed to ${action === "unlink" ? "unlink" : action} the relationship.`);
    } finally {
      setConfirmationAction(null);
    }
  };

  const facilityOptions = useMemo(
    () =>
      facilities.map((facility) => ({
        value: facility.id,
        label: facility.name,
      })),
    [facilities]
  );

  const agencyOptions = useMemo(
    () =>
      agencies.map((agency) => ({
        value: agency.id,
        label: agency.name,
      })),
    [agencies]
  );

  // Filter pending (invited) relationships for Section 2
  const pendingRelationships = useMemo(
    () => relationships.filter((rel) => rel.status === "invited"),
    [relationships]
  );

  // Combined company list for Section 3 dropdown (sorted alphabetically)
  const allCompaniesForLinks = useMemo(() => {
    const combined = [
      ...facilities.map((f) => ({ ...f, type: "facility", displayName: `${f.name} - Facility` })),
      ...agencies.map((a) => ({ ...a, type: "agency", displayName: `${a.name} - Agency` })),
    ];
    return combined.sort((a, b) => a.name.localeCompare(b.name));
  }, [facilities, agencies]);

  // Filter relationships for the selected company in Section 3
  const filteredRelationshipsForCompany = useMemo(() => {
    if (!selectedCompanyForLinks) return [];

    if (selectedCompanyForLinks.type === "facility") {
      // If facility is selected, show relationships where it's the facility
      return relationships.filter((rel) => rel.facility_id === selectedCompanyForLinks.id);
    } else {
      // If agency is selected, show relationships where it's the agency
      return relationships.filter((rel) => rel.agency_id === selectedCompanyForLinks.id);
    }
  }, [selectedCompanyForLinks, relationships]);

  return (
    <section className="page dashboard">
      <header className="page-header">
        <h2>Platform Admin Console</h2>
        <p className="muted">
          Create facilities and agencies, connect them, and monitor pending shift claims.
        </p>
      </header>

      {loading ? <div className="card">Loading data�</div> : null}
      {message ? <div className="banner success">{message}</div> : null}

      <div style={{ marginBottom: "2rem" }}>
        <button
          onClick={() => setShowAddCompanyModal(true)}
          className="primary"
          style={{
            fontSize: "1rem",
            padding: "0.75rem 1.5rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem"
          }}
        >
          <span style={{ fontSize: "1.25rem" }}>➕</span>
          Add Company
        </button>
      </div>

      <section className="card">
        <h3>Link Facility to Agency</h3>
        <form className="form inline" onSubmit={handleRelationshipSubmit}>
          <label>
            Facility
            <select
              value={relationshipForm.facility_id}
              onChange={(event) =>
                setRelationshipForm((prev) => ({ ...prev, facility_id: event.target.value }))
              }
              required
            >
              <option value="">Select facility</option>
              {facilityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Agency
            <select
              value={relationshipForm.agency_id}
              onChange={(event) =>
                setRelationshipForm((prev) => ({ ...prev, agency_id: event.target.value }))
              }
              required
            >
              <option value="">Select agency</option>
              {agencyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" className="primary">
            Link
          </button>
        </form>
      </section>

      <section className="card">
        <h3>Pending Link Approvals</h3>
        <div className="card-body">
          {pendingRelationships.length === 0 ? (
            <p className="muted">No pending link requests</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Facility</th>
                  <th>Agency</th>
                  <th>Requested By</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pendingRelationships.map((rel) => {
                  const facility = facilities.find((item) => item.id === rel.facility_id);
                  const agency = agencies.find((item) => item.id === rel.agency_id);
                  return (
                    <tr key={rel.id}>
                      <td>{facility ? facility.name : rel.facility_id}</td>
                      <td>{agency ? agency.name : rel.agency_id}</td>
                      <td>{rel.requested_by || "—"}</td>
                      <td>
                        <div className="button-row">
                          <button
                            type="button"
                            onClick={() => showConfirmation("activate", rel.id, { facility, agency })}
                          >
                            Activate
                          </button>
                          <button
                            type="button"
                            onClick={() => showConfirmation("revoke", rel.id, { facility, agency })}
                          >
                            Revoke
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="card">
        <h3>View Company Links</h3>
        <div className="card-body">
          <label>
            Select Company
            <select
              value={selectedCompanyForLinks ? `${selectedCompanyForLinks.type}:::${selectedCompanyForLinks.id}` : ""}
              onChange={(e) => {
                const value = e.target.value;
                if (value) {
                  const separatorIndex = value.indexOf(":::");
                  const type = value.substring(0, separatorIndex);
                  const id = value.substring(separatorIndex + 3);
                  const company = allCompaniesForLinks.find((c) => c.type === type && c.id === id);
                  setSelectedCompanyForLinks(company);
                } else {
                  setSelectedCompanyForLinks(null);
                }
              }}
            >
              <option value="">Select a company...</option>
              {allCompaniesForLinks.map((company) => (
                <option key={`${company.type}-${company.id}`} value={`${company.type}:::${company.id}`}>
                  {company.displayName}
                </option>
              ))}
            </select>
          </label>

          {selectedCompanyForLinks && (
            <div style={{ marginTop: "1.5rem" }}>
              <h4>Links for {selectedCompanyForLinks.name}</h4>
              {filteredRelationshipsForCompany.length === 0 ? (
                <p className="muted">No links found for this company</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Linked Company</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Created Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRelationshipsForCompany.map((rel) => {
                      const isSelectedFacility = selectedCompanyForLinks.type === "facility";
                      const linkedCompanyId = isSelectedFacility ? rel.agency_id : rel.facility_id;
                      const linkedCompanyType = isSelectedFacility ? "agency" : "facility";
                      const linkedCompanyList = isSelectedFacility ? agencies : facilities;
                      const linkedCompany = linkedCompanyList.find((c) => c.id === linkedCompanyId);

                      // Get facility and agency for confirmation dialog
                      const facility = facilities.find((f) => f.id === rel.facility_id);
                      const agency = agencies.find((a) => a.id === rel.agency_id);

                      return (
                        <tr key={rel.id}>
                          <td>{linkedCompany ? linkedCompany.name : linkedCompanyId}</td>
                          <td style={{ textTransform: "capitalize" }}>{linkedCompanyType}</td>
                          <td>
                            <span className={`badge status-${rel.status}`}>{rel.status}</span>
                          </td>
                          <td>{rel.created_at ? dayjs(rel.created_at).format("MMM D, YYYY") : "—"}</td>
                          <td>
                            {rel.status === "active" && (
                              <button
                                type="button"
                                onClick={() => showConfirmation("unlink", rel.id, { facility, agency })}
                                style={{ fontSize: "0.875rem", padding: "0.375rem 0.75rem" }}
                              >
                                Unlink
                              </button>
                            )}
                            {rel.status === "revoked" && (
                              <span className="muted" style={{ fontSize: "0.875rem" }}>Already revoked</span>
                            )}
                            {rel.status === "invited" && (
                              <span className="muted" style={{ fontSize: "0.875rem" }}>Pending</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </section>

      <div className="grid two-column">
        <section className="card">
          <h3>All Facilities</h3>
          <div className="card-body">
            {facilities.length === 0 ? (
              <p className="muted">No facilities created yet.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Address</th>
                  </tr>
                </thead>
                <tbody>
                  {facilities.map((facility) => (
                    <tr key={facility.id}>
                      <td>
                        <strong style={{ color: "#2563eb" }}>{facility.display_id}</strong>
                      </td>
                      <td>
                        <button
                          onClick={() => setSelectedCompany(facility)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "#2563eb",
                            cursor: "pointer",
                            textDecoration: "underline",
                            padding: 0,
                            font: "inherit"
                          }}
                        >
                          {facility.name}
                        </button>
                      </td>
                      <td>{facility.address || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <section className="card">
          <h3>All Agencies</h3>
          <div className="card-body">
            {agencies.length === 0 ? (
              <p className="muted">No agencies created yet.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Address</th>
                  </tr>
                </thead>
                <tbody>
                  {agencies.map((agency) => (
                    <tr key={agency.id}>
                      <td>
                        <strong style={{ color: "#059669" }}>{agency.display_id}</strong>
                      </td>
                      <td>
                        <button
                          onClick={() => setSelectedCompany(agency)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "#059669",
                            cursor: "pointer",
                            textDecoration: "underline",
                            padding: 0,
                            font: "inherit"
                          }}
                        >
                          {agency.name}
                        </button>
                      </td>
                      <td>{agency.address || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>

      <section className="card">
        <h3>Pending Claims Across Platform</h3>
        <div className="card-body">
          {pendingClaims.length === 0 ? (
            <p className="muted">No pending claims right now.</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Claim ID</th>
                  <th>Shift</th>
                  <th>Clinician</th>
                  <th>Requested</th>
                </tr>
              </thead>
              <tbody>
                {pendingClaims.map((claim) => (
                  <tr key={claim.id}>
                    <td>{claim.id}</td>
                    <td>{claim.shift_id}</td>
                    <td>{claim.user_id}</td>
                    <td>{dayjs(claim.claimed_at).format("MMM D, YYYY h:mm A")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {selectedCompany && (
        <CompanyInfoModal
          company={selectedCompany}
          onClose={() => setSelectedCompany(null)}
          onUpdate={loadData}
        />
      )}

      {showAddCompanyModal && (
        <AddCompanyModal
          onClose={() => setShowAddCompanyModal(false)}
          onSuccess={handleCompanyCreated}
        />
      )}

      {confirmationAction && (
        <div className="modal-overlay" onClick={cancelConfirmation}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h2>
                {confirmationAction.action === "activate"
                  ? "Confirm Activation"
                  : confirmationAction.action === "unlink"
                  ? "Confirm Unlink"
                  : "Confirm Revocation"}
              </h2>
              <button className="close-button" onClick={cancelConfirmation}>
                ×
              </button>
            </div>

            <div className="modal-body">
              <div
                className={`banner ${confirmationAction.action === "activate" ? "info" : "warning"}`}
                style={{ marginBottom: "1rem" }}
              >
                {confirmationAction.action === "activate"
                  ? "Are you sure you want to activate this relationship? This will allow the agency to see and claim shifts from the facility."
                  : confirmationAction.action === "unlink"
                  ? "Are you sure you want to unlink these companies? This will end the active relationship and prevent the agency from seeing new shifts from this facility."
                  : "Are you sure you want to revoke this relationship? This will prevent the agency from seeing new shifts from the facility."}
              </div>

              <div style={{ backgroundColor: "#f9fafb", padding: "1rem", borderRadius: "8px" }}>
                <h3 style={{ marginBottom: "0.75rem", fontSize: "1rem", color: "#374151" }}>
                  Relationship Details
                </h3>
                <div style={{ display: "grid", gap: "0.5rem" }}>
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "100px", color: "#6b7280" }}>Facility:</strong>
                    <span>
                      {confirmationAction.relationship?.facility?.name || "Unknown Facility"}
                    </span>
                  </div>
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "100px", color: "#6b7280" }}>Agency:</strong>
                    <span>
                      {confirmationAction.relationship?.agency?.name || "Unknown Agency"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" onClick={cancelConfirmation}>
                Cancel
              </button>
              <button
                type="button"
                className={confirmationAction.action === "activate" ? "primary" : "danger"}
                onClick={executeAction}
              >
                {confirmationAction.action === "activate"
                  ? "Confirm Activation"
                  : confirmationAction.action === "unlink"
                  ? "Confirm Unlink"
                  : "Confirm Revocation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default SuperAdminDashboard;
