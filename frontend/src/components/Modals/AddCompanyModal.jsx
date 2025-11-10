import { useState } from "react";
import { createFacility, createAgency } from "../../services/backend";

const timezones = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
];

function AddCompanyModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    type: "facility",
    name: "",
    address: "",
    phone: "",
    contact_email: "",
    timezone: timezones[0],
    admin_name: "",
    admin_username: "",
    admin_email: "",
    admin_password: "",
    admin_password_confirm: "",
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Company name is required";
    }

    if (!formData.admin_name.trim()) {
      newErrors.admin_name = "Admin name is required";
    }

    if (!formData.admin_username.trim()) {
      newErrors.admin_username = "Admin username is required";
    }

    if (!formData.admin_password) {
      newErrors.admin_password = "Password is required";
    } else if (formData.admin_password.length < 8) {
      newErrors.admin_password = "Password must be at least 8 characters";
    }

    if (formData.admin_password !== formData.admin_password_confirm) {
      newErrors.admin_password_confirm = "Passwords do not match";
    }

    if (formData.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contact_email)) {
      newErrors.contact_email = "Invalid email format";
    }

    if (formData.admin_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.admin_email)) {
      newErrors.admin_email = "Invalid email format";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Show confirmation dialog
    setShowConfirmation(true);
  };

  const handleConfirmCreate = async () => {
    setSubmitting(true);
    try {
      const payload = {
        type: formData.type,
        name: formData.name,
        address: formData.address || null,
        phone: formData.phone || null,
        contact_email: formData.contact_email || null,
        timezone: formData.timezone,
        admin_username: formData.admin_username,
        admin_password: formData.admin_password,
        admin_name: formData.admin_name,
        admin_email: formData.admin_email || null,
        admin_phone: null, // Not in form currently
      };

      let created;
      if (formData.type === "facility") {
        created = await createFacility(payload);
      } else {
        created = await createAgency(payload);
      }

      if (onSuccess) {
        onSuccess(created);
      }
      setSubmitting(false);
      onClose();
    } catch (error) {
      setErrors({
        submit: error.response?.data?.detail || error.message || "Failed to create company",
      });
      setShowConfirmation(false);
      setSubmitting(false);
    }
  };

  const handleCancelConfirmation = () => {
    setShowConfirmation(false);
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Render confirmation dialog
  if (showConfirmation) {
    return (
      <div className="modal-overlay" onClick={handleCancelConfirmation}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "600px" }}>
          <div className="modal-header">
            <h2>Confirm Company Creation</h2>
            <button className="close-button" onClick={handleCancelConfirmation} disabled={submitting}>
              ×
            </button>
          </div>

          <div className="modal-body">
            <div className="banner info" style={{ marginBottom: "1rem" }}>
              Please review the information below and confirm to create this company and its administrator account.
            </div>

            <div style={{ backgroundColor: "#f9fafb", padding: "1rem", borderRadius: "8px", marginBottom: "1rem" }}>
              <h3 style={{ marginBottom: "0.75rem", fontSize: "1rem", color: "#374151" }}>Company Details</h3>
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Type:</strong>
                  <span style={{ textTransform: "capitalize" }}>{formData.type}</span>
                </div>
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Name:</strong>
                  <span>{formData.name}</span>
                </div>
                {formData.address && (
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "140px", color: "#6b7280" }}>Address:</strong>
                    <span>{formData.address}</span>
                  </div>
                )}
                {formData.phone && (
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "140px", color: "#6b7280" }}>Phone:</strong>
                    <span>{formData.phone}</span>
                  </div>
                )}
                {formData.contact_email && (
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "140px", color: "#6b7280" }}>Contact Email:</strong>
                    <span>{formData.contact_email}</span>
                  </div>
                )}
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Timezone:</strong>
                  <span>{formData.timezone}</span>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: "#f0f9ff", padding: "1rem", borderRadius: "8px" }}>
              <h3 style={{ marginBottom: "0.75rem", fontSize: "1rem", color: "#374151" }}>Administrator Account</h3>
              <div style={{ display: "grid", gap: "0.5rem" }}>
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Name:</strong>
                  <span>{formData.admin_name}</span>
                </div>
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Username:</strong>
                  <span>{formData.admin_username}</span>
                </div>
                {formData.admin_email && (
                  <div style={{ display: "flex" }}>
                    <strong style={{ width: "140px", color: "#6b7280" }}>Email:</strong>
                    <span>{formData.admin_email}</span>
                  </div>
                )}
                <div style={{ display: "flex" }}>
                  <strong style={{ width: "140px", color: "#6b7280" }}>Password:</strong>
                  <span>••••••••</span>
                </div>
              </div>
            </div>

            {errors.submit && (
              <div className="banner error" style={{ marginTop: "1rem" }}>
                {errors.submit}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" onClick={handleCancelConfirmation} disabled={submitting}>
              Go Back
            </button>
            <button type="button" className="primary" onClick={handleConfirmCreate} disabled={submitting}>
              {submitting ? "Creating..." : "Confirm & Create"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render form
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "50%", minWidth: "500px" }}>
        <div className="modal-header">
          <h2>Add New Company</h2>
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.submit && (
              <div className="banner error" style={{ marginBottom: "1rem" }}>
                {errors.submit}
              </div>
            )}

            <h3 style={{ marginBottom: "1rem", fontSize: "1.1rem", borderBottom: "1px solid #e5e7eb", paddingBottom: "0.5rem" }}>
              Company Information
            </h3>

            <label>
              Company Type <span style={{ color: "#dc2626" }}>*</span>
              <select
                value={formData.type}
                onChange={(e) => handleChange("type", e.target.value)}
                required
              >
                <option value="facility">Facility</option>
                <option value="agency">Agency</option>
              </select>
            </label>

            <label>
              Company Name <span style={{ color: "#dc2626" }}>*</span>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                required
              />
              {errors.name && <span className="error-text">{errors.name}</span>}
            </label>

            <label>
              Address
              <input
                type="text"
                value={formData.address}
                onChange={(e) => handleChange("address", e.target.value)}
              />
            </label>

            <label>
              Phone Number
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange("phone", e.target.value)}
                placeholder="(555) 123-4567"
              />
            </label>

            <label>
              Company Contact Email
              <input
                type="email"
                value={formData.contact_email}
                onChange={(e) => handleChange("contact_email", e.target.value)}
                placeholder="contact@company.com"
              />
              {errors.contact_email && <span className="error-text">{errors.contact_email}</span>}
            </label>

            <label>
              Timezone
              <select
                value={formData.timezone}
                onChange={(e) => handleChange("timezone", e.target.value)}
              >
                {timezones.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </label>

            <h3 style={{ marginTop: "1.5rem", marginBottom: "1rem", fontSize: "1.1rem", borderBottom: "1px solid #e5e7eb", paddingBottom: "0.5rem" }}>
              Administrator Account
            </h3>

            <label>
              Admin Name <span style={{ color: "#dc2626" }}>*</span>
              <input
                type="text"
                value={formData.admin_name}
                onChange={(e) => handleChange("admin_name", e.target.value)}
                required
                placeholder="John Doe"
              />
              {errors.admin_name && <span className="error-text">{errors.admin_name}</span>}
            </label>

            <label>
              Admin Username <span style={{ color: "#dc2626" }}>*</span>
              <input
                type="text"
                value={formData.admin_username}
                onChange={(e) => handleChange("admin_username", e.target.value)}
                required
                placeholder="admin.johndoe"
              />
              {errors.admin_username && <span className="error-text">{errors.admin_username}</span>}
            </label>

            <label>
              Admin Email (optional)
              <input
                type="email"
                value={formData.admin_email}
                onChange={(e) => handleChange("admin_email", e.target.value)}
                placeholder="admin@company.com"
              />
              {errors.admin_email && <span className="error-text">{errors.admin_email}</span>}
            </label>

            <label>
              Admin Password <span style={{ color: "#dc2626" }}>*</span>
              <input
                type="password"
                value={formData.admin_password}
                onChange={(e) => handleChange("admin_password", e.target.value)}
                required
                minLength={8}
                placeholder="Minimum 8 characters"
              />
              {errors.admin_password && <span className="error-text">{errors.admin_password}</span>}
            </label>

            <label>
              Confirm Password <span style={{ color: "#dc2626" }}>*</span>
              <input
                type="password"
                value={formData.admin_password_confirm}
                onChange={(e) => handleChange("admin_password_confirm", e.target.value)}
                required
                minLength={8}
                placeholder="Re-enter password"
              />
              {errors.admin_password_confirm && <span className="error-text">{errors.admin_password_confirm}</span>}
            </label>
          </div>

          <div className="modal-footer">
            <button type="button" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={submitting}>
              Review & Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddCompanyModal;
