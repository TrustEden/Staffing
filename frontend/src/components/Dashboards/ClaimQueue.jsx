const mockClaims = [
  { id: "1", shift: "RN – 07:00-15:00", claimant: "Alexis Stone", status: "Pending" },
  { id: "2", shift: "CNA – 15:00-23:00", claimant: "Jamie Fox", status: "Pending" }
];

function ClaimQueue() {
  return (
    <section>
      <h2>Claim Approval Queue</h2>
      <table className="data-table">
        <thead>
          <tr>
            <th>Shift</th>
            <th>Clinician</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {mockClaims.map((claim) => (
            <tr key={claim.id}>
              <td>{claim.shift}</td>
              <td>{claim.claimant}</td>
              <td>{claim.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default ClaimQueue;
