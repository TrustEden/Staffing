import api from "./api";

export async function fetchCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function fetchFacilities() {
  const { data } = await api.get("/facilities/");
  return data;
}

export async function createFacility(payload) {
  const { data } = await api.post("/facilities/", payload);
  return data;
}

export async function fetchAgencies() {
  const { data } = await api.get("/agencies/");
  return data;
}

export async function createAgency(payload) {
  const { data } = await api.post("/agencies/", payload);
  return data;
}

export async function listRelationships() {
  const { data } = await api.get("/admin/relationships");
  return data;
}

export async function createRelationship(payload) {
  const { data } = await api.post("/admin/relationships", payload);
  return data;
}

export async function updateRelationshipStatus(relationshipId, status) {
  const { data } = await api.patch(`/admin/relationships/${relationshipId}`, { status });
  return data;
}

export async function requestAgencyLink(facilityId, agencyDisplayId) {
  const { data } = await api.post(`/facilities/${facilityId}/request-link`, {
    agency_display_id: agencyDisplayId,
  });
  return data;
}

export async function requestFacilityLink(agencyId, facilityDisplayId) {
  const { data } = await api.post(`/agencies/${agencyId}/request-link`, {
    facility_display_id: facilityDisplayId,
  });
  return data;
}

export async function fetchFacilityRelationships(facilityId) {
  const { data } = await api.get(`/facilities/${facilityId}/all-relationships`);
  return data;
}

export async function fetchAgencyRelationships(agencyId) {
  const { data } = await api.get(`/agencies/${agencyId}/all-relationships`);
  return data;
}

export async function fetchFacilityStaff(facilityId) {
  const { data } = await api.get(`/facilities/${facilityId}/staff`);
  return data;
}

export async function addFacilityStaff(facilityId, payload) {
  const { data } = await api.post(`/facilities/${facilityId}/staff`, payload);
  return data;
}

export async function fetchAgencyStaff(agencyId) {
  const { data } = await api.get(`/agencies/${agencyId}/staff`);
  return data;
}

export async function addAgencyStaff(agencyId, payload) {
  const { data } = await api.post(`/agencies/${agencyId}/staff`, payload);
  return data;
}

export async function fetchAgencyFacilities(agencyId) {
  const { data } = await api.get(`/agencies/${agencyId}/relationships`);
  return data;
}

export async function fetchShifts(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, value);
    }
  });
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const { data } = await api.get(`/shifts/${suffix}`);
  return data;
}

export async function createShift(payload) {
  const { data } = await api.post("/shifts/", payload);
  return data;
}

export async function cancelShift(shiftId) {
  const { data } = await api.post(`/shifts/${shiftId}/cancel`);
  return data;
}

export async function fetchShiftClaims(shiftId) {
  const { data } = await api.get(`/shifts/${shiftId}/claims`);
  return data;
}

export async function approveClaim(shiftId, claimId) {
  const { data } = await api.post(`/shifts/${shiftId}/claims/${claimId}/approve`);
  return data;
}

export async function denyClaim(shiftId, claimId, reason) {
  const { data } = await api.post(`/shifts/${shiftId}/claims/${claimId}/deny`, {
    reason: reason || null,
  });
  return data;
}

export async function claimShift(shiftId) {
  const { data } = await api.post(`/shifts/${shiftId}/claims`);
  return data;
}

export async function uploadShifts(facilityId, file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(`/uploads/shifts?facility_id=${facilityId}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listNotifications(unreadOnly = false) {
  const suffix = unreadOnly ? "?unread_only=true" : "";
  const { data } = await api.get(`/notifications/${suffix}`);
  return data;
}

export async function markNotification(notificationId, read) {
  const { data } = await api.post(`/notifications/${notificationId}/read`, { read });
  return data;
}

export async function markAllNotificationsRead() {
  await api.post("/notifications/mark-all-read");
}

export async function fetchPendingClaims() {
  const { data } = await api.get("/admin/claims/pending");
  return data;
}

export async function fetchMyClaims() {
  const { data } = await api.get("/claims/me");
  return data;
}

export async function fetchCompanyStats(companyId) {
  const { data } = await api.get(`/admin/companies/${companyId}/stats`);
  return data;
}

export async function updateCompanyLockStatus(companyId, isLocked) {
  const { data } = await api.patch(`/admin/companies/${companyId}/lock`, { is_locked: isLocked });
  return data;
}

export async function resetCompanyAdminPassword(companyId, newPassword) {
  const { data } = await api.post(`/admin/companies/${companyId}/reset-admin-password`, { new_password: newPassword });
  return data;
}
