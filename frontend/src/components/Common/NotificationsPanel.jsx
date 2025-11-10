import PropTypes from "prop-types";
import dayjs from "dayjs";

function NotificationsPanel({ notifications, onMarkRead, onMarkAll }) {
  return (
    <section className="card">
      <header className="card-header">
        <h3>Notifications</h3>
        {notifications.length ? (
          <button type="button" className="link-button" onClick={onMarkAll}>
            Mark all read
          </button>
        ) : null}
      </header>
      <div className="card-body">
        {notifications.length === 0 ? (
          <p className="muted">No notifications yet.</p>
        ) : (
          <ul className="notification-list">
            {notifications.map((note) => (
              <li key={note.id} className={note.read ? "" : "unread"}>
                <div>
                  <strong>{note.type.replaceAll("_", " ")}</strong>
                  <p>{note.content}</p>
                  <span className="muted">
                    {dayjs(note.created_at).format("MMM D, YYYY h:mm A")}
                  </span>
                </div>
                {!note.read ? (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onMarkRead(note.id, true)}
                  >
                    Mark read
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

NotificationsPanel.propTypes = {
  notifications: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      type: PropTypes.string.isRequired,
      content: PropTypes.string.isRequired,
      read: PropTypes.bool.isRequired,
      created_at: PropTypes.string.isRequired,
    })
  ).isRequired,
  onMarkRead: PropTypes.func.isRequired,
  onMarkAll: PropTypes.func.isRequired,
};

export default NotificationsPanel;
