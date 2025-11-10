const mockShifts = [
  { id: "1", facility: "Sunrise Care Center", role: "RN", window: "07:00 - 15:00", visibility: "Internal", status: "Open" },
  { id: "2", facility: "Sunrise Care Center", role: "CNA", window: "15:00 - 23:00", visibility: "Tiered", status: "Pending" }
];

function ShiftBoard() {
  return (
    <section>
      <h2>Shift Board</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Facility</th>
            <th>Window</th>
            <th>Visibility</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {mockShifts.map((shift) => (
            <tr key={shift.id}>
              <td>{shift.role}</td>
              <td>{shift.facility}</td>
              <td>{shift.window}</td>
              <td>{shift.visibility}</td>
              <td>{shift.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default ShiftBoard;
