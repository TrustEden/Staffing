function Home() {
  return (
    <section className="page">
      <h2>Healthcare Staffing Bridge Demo</h2>
      <p>
        Sign in as the platform administrator to create facilities and agencies, connect them,
        invite staff, upload schedules, and watch clinicians claim shifts in real time.
      </p>
      <div className="card list-card">
        <h3>Demo Flow</h3>
        <ol>
          <li>Login with the seeded platform admin: <code>superadmin@example.com</code> / <code>ChangeMe123!</code>.</li>
          <li>Create a facility and an agency, then link them in the relationships tab.</li>
          <li>Add a facility admin + internal staff, plus agency admin/staff accounts.</li>
          <li>Upload a facility shift schedule or add a few shifts manually.</li>
          <li>Log in as staff or agency members, claim shifts, and approve them as the facility admin.</li>
        </ol>
      </div>
    </section>
  );
}

export default Home;
