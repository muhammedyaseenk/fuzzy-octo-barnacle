-- database_notification_schema.sql
-- Notification infrastructure tables

-- User devices for push notifications
CREATE TABLE IF NOT EXISTS user_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN ('android', 'ios', 'web')),
    device_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_devices_user ON user_devices(user_id, is_active);
CREATE UNIQUE INDEX idx_user_devices_token ON user_devices(device_token);

-- Notification logs
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL CHECK (type IN ('push', 'email', 'sms', 'in_app')),
    title VARCHAR(255),
    message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'pending'))
);

CREATE INDEX idx_notification_logs_user ON notification_logs(user_id, sent_at DESC);
CREATE INDEX idx_notification_logs_status ON notification_logs(status, sent_at DESC);

-- Notification failures for admin monitoring
CREATE TABLE IF NOT EXISTS notification_failures (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notification_failures_created ON notification_failures(created_at DESC);
CREATE INDEX idx_notification_failures_channel ON notification_failures(channel, created_at DESC);

-- User notification preferences
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    push_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    new_matches BOOLEAN DEFAULT TRUE,
    new_messages BOOLEAN DEFAULT TRUE,
    profile_views BOOLEAN DEFAULT TRUE,
    interests BOOLEAN DEFAULT TRUE,
    marketing BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notification_prefs_user ON notification_preferences(user_id);

-- Function to cleanup old logs
CREATE OR REPLACE FUNCTION cleanup_old_notification_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notification_logs
    WHERE sent_at < NOW() - INTERVAL '90 days'
    AND status = 'sent';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- View for notification stats
CREATE OR REPLACE VIEW v_notification_stats AS
SELECT 
    DATE(sent_at) as date,
    type,
    status,
    COUNT(*) as count
FROM notification_logs
WHERE sent_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(sent_at), type, status
ORDER BY date DESC, type;

-- Sample device data
INSERT INTO user_devices (user_id, device_token, device_type, device_name)
SELECT 
    id,
    'fcm_token_' || id || '_' || MD5(RANDOM()::TEXT),
    CASE WHEN RANDOM() < 0.5 THEN 'android' ELSE 'ios' END,
    'Device ' || id
FROM users
WHERE id NOT IN (SELECT user_id FROM user_devices)
LIMIT 100
ON CONFLICT DO NOTHING;

-- Sample notification preferences
INSERT INTO notification_preferences (user_id)
SELECT id FROM users
WHERE id NOT IN (SELECT user_id FROM notification_preferences)
ON CONFLICT (user_id) DO NOTHING;

ANALYZE user_devices;
ANALYZE notification_logs;
ANALYZE notification_failures;
ANALYZE notification_preferences;
