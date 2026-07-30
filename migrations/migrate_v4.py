"""Migration v4: Persist per-user dashboard widget preferences."""


def migrate(conn):
    """Create the dashboard_widget_preferences table."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboard_widget_preferences (
            user_id INTEGER PRIMARY KEY,
            widgets_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
