export default function SettingsAccountPage() {
  return (
    <article className="glass-card">
      <header>
        <span>ACCOUNT</span>
      </header>
      <p>
        Sign-in is Clerk. Role and entitlement live in Vroometr&apos;s database, not in
        the browser.
      </p>
      <ul className="settings-list">
        <li>Profile and email — Clerk</li>
        <li>Role / plan — Vroometr (read-only here until billing)</li>
        <li>Age eligibility — API hooks exist; Settings UI later</li>
        <li>Garage bikes — API at /v1/bikes; garage pages later</li>
        <li>Assistant memory controls — later; they will live in Settings</li>
      </ul>
    </article>
  );
}
