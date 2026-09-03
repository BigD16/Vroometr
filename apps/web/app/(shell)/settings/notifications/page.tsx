export default function SettingsNotificationsPage() {
  return (
    <article className="glass-card">
      <header>
        <span>NOTIFICATIONS</span>
      </header>
      <p>In-app and email. Per-category controls land with the notification service.</p>
      <ul className="settings-list">
        <li>
          <span>Maintenance due / overdue</span>
          <small>Off until notifications ship</small>
        </li>
        <li>
          <span>Pre-ride recommendation</span>
          <small>Off until notifications ship</small>
        </li>
        <li>
          <span>Post-ride follow-up</span>
          <small>Off until notifications ship</small>
        </li>
        <li>
          <span>Document processing</span>
          <small>Off until notifications ship</small>
        </li>
        <li>
          <span>Payment failure</span>
          <small>Always on — cannot disable</small>
        </li>
        <li>
          <span>Approaching account / data deletion</span>
          <small>Always on — cannot disable</small>
        </li>
      </ul>
    </article>
  );
}
