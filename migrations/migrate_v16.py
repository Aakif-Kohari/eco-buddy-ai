import sqlite3

def migrate(conn: sqlite3.Connection) -> None:
    """Apply migration version 16: Add Inbound Webhooks & Automation tables."""
    
    # 1. Table for webhook configuration
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inbound_webhooks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            secure_token TEXT UNIQUE NOT NULL,
            app_name TEXT NOT NULL,
            action_template TEXT NOT NULL,
            mapping_rules TEXT,  -- JSON string containing JSONPath rules
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    
    # 2. Table for webhook event logs
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_event_logs (
            id TEXT PRIMARY KEY,
            webhook_id TEXT NOT NULL,
            payload TEXT,      -- Raw JSON payload string
            status TEXT NOT NULL,  -- 'SUCCESS' or 'FAILED'
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (webhook_id) REFERENCES inbound_webhooks (id) ON DELETE CASCADE
        );
        """
    )

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inbound_webhooks_user ON inbound_webhooks (user_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inbound_webhooks_token ON inbound_webhooks (secure_token);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_webhook_logs_webhook ON webhook_event_logs (webhook_id);")

    conn.commit()
