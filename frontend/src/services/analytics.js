import api from "./api";

/**
 * Get fill rate percentage over time
 * @param {string} facilityId - The facility ID to filter by
 * @param {string} startDate - Start date in ISO format
 * @param {string} endDate - End date in ISO format
 * @returns {Promise<Array>} Array of {date, fillRate, totalShifts, filledShifts}
 */
export async function getFillRate(facilityId, startDate, endDate) {
  try {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    if (facilityId) {
      params.append("facility_id", facilityId);
    }

    const response = await api.get(`/analytics/fill-rate?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch fill rate data:", error);
    throw error;
  }
}

/**
 * Get average time to fill shifts by week
 * @param {string} facilityId - The facility ID to filter by
 * @param {string} startDate - Start date in ISO format
 * @param {string} endDate - End date in ISO format
 * @returns {Promise<Array>} Array of {week, avgHours, shiftCount}
 */
export async function getTimeToFill(facilityId, startDate, endDate) {
  try {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    if (facilityId) {
      params.append("facility_id", facilityId);
    }

    const response = await api.get(`/analytics/time-to-fill?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch time to fill data:", error);
    throw error;
  }
}

/**
 * Get shift statistics breakdown
 * @param {string} facilityId - The facility ID to filter by
 * @param {string} startDate - Start date in ISO format
 * @param {string} endDate - End date in ISO format
 * @returns {Promise<Object>} Object with total, byStatus, byTier
 */
export async function getShiftStats(facilityId, startDate, endDate) {
  try {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    if (facilityId) {
      params.append("facility_id", facilityId);
    }

    const response = await api.get(`/analytics/shift-stats?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch shift stats:", error);
    throw error;
  }
}

/**
 * Get agency performance metrics
 * @param {string} agencyId - The agency ID
 * @param {string} startDate - Start date in ISO format
 * @param {string} endDate - End date in ISO format
 * @returns {Promise<Object>} Performance metrics for the agency
 */
export async function getAgencyPerformance(agencyId, startDate, endDate) {
  try {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });

    const response = await api.get(`/analytics/agency/${agencyId}/performance?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch agency performance:", error);
    throw error;
  }
}

/**
 * Get shift density by day for heatmap visualization
 * @param {string} facilityId - The facility ID to filter by
 * @param {string} startDate - Start date in ISO format
 * @param {string} endDate - End date in ISO format
 * @returns {Promise<Array>} Array of {date, count, status}
 */
export async function getShiftDensity(facilityId, startDate, endDate) {
  try {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    if (facilityId) {
      params.append("facility_id", facilityId);
    }

    const response = await api.get(`/analytics/shift-density?${params.toString()}`);
    return response.data;
  } catch (error) {
    console.error("Failed to fetch shift density:", error);
    throw error;
  }
}
