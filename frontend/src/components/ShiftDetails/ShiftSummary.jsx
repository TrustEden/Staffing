function ShiftSummary({ shift }) {
  if (!shift) {
    return (
      <div className="card">
        <h3>Select a shift to see details</h3>
        <p>Claim history and conflict warnings will appear here.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>{shift.role}</h3>
      <p>
        <strong>Facility:</strong> {shift.facility}
      </p>
      <p>
        <strong>Window:</strong> {shift.window}
      </p>
      <p>
        <strong>Status:</strong> {shift.status}
      </p>
    </div>
  );
}

export default ShiftSummary;
