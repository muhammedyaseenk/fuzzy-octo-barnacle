-- database_whatsapp_schema.sql
-- WhatsApp messaging infrastructure with security

-- WhatsApp message log (all messages)
CREATE TABLE IF NOT EXISTS whatsapp_message_log (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_content TEXT NOT NULL,
    whatsapp_message_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'sent', 'failed', 'blocked')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_whatsapp_log_sender ON whatsapp_message_log(sender_id, created_at DESC);
CREATE INDEX idx_whatsapp_log_recipient ON whatsapp_message_log(recipient_id, created_at DESC);
CREATE INDEX idx_whatsapp_log_status ON whatsapp_message_log(status, created_at DESC);

-- Content violations (security tracking)
CREATE TABLE IF NOT EXISTS content_violations (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    message_content TEXT NOT NULL,
    violation_reason TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical', 'harmful', 'ai_flagged')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_violations_sender ON content_violations(sender_id, created_at DESC);
CREATE INDEX idx_violations_severity ON content_violations(severity, created_at DESC);

-- Admin reviews for flagged messages
CREATE TABLE IF NOT EXISTS whatsapp_admin_reviews (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_content TEXT NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approve', 'reject')),
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_admin_reviews_sender ON whatsapp_admin_reviews(sender_id, created_at DESC);
CREATE INDEX idx_admin_reviews_admin ON whatsapp_admin_reviews(admin_id, created_at DESC);

-- Add WhatsApp field to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS whatsapp VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_users_whatsapp ON users(whatsapp) WHERE whatsapp IS NOT NULL;

-- View for admin dashboard
CREATE OR REPLACE VIEW v_whatsapp_stats AS
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as message_count
FROM whatsapp_message_log
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), status
ORDER BY date DESC;

CREATE OR REPLACE VIEW v_violation_stats AS
SELECT 
    sender_id,
    COUNT(*) as violation_count,
    MAX(severity) as max_severity,
    MAX(created_at) as last_violation
FROM content_violations
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY sender_id
HAVING COUNT(*) >= 2
ORDER BY violation_count DESC;

-- Function to get user violation count
CREATE OR REPLACE FUNCTION get_user_violation_count(p_user_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM content_violations
        WHERE sender_id = p_user_id
        AND created_at >= NOW() - INTERVAL '30 days'
    );
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-block users after 3 violations
CREATE OR REPLACE FUNCTION check_violation_threshold()
RETURNS TRIGGER AS $$
DECLARE
    violation_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO violation_count
    FROM content_violations
    WHERE sender_id = NEW.sender_id
    AND created_at >= NOW() - INTERVAL '7 days';
    
    IF violation_count >= 3 THEN
        -- Log critical alert
        INSERT INTO admin_alerts (alert_type, user_id, message, severity, created_at)
        VALUES ('auto_block', NEW.sender_id, 
                'User auto-blocked after ' || violation_count || ' violations', 
                'critical', NOW());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_violations
AFTER INSERT ON content_violations
FOR EACH ROW
EXECUTE FUNCTION check_violation_threshold();

-- Admin alerts table
CREATE TABLE IF NOT EXISTS admin_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_admin_alerts_unresolved ON admin_alerts(resolved, created_at DESC) WHERE resolved = FALSE;
CREATE INDEX idx_admin_alerts_severity ON admin_alerts(severity, created_at DESC);

ANALYZE whatsapp_message_log;
ANALYZE content_violations;
ANALYZE whatsapp_admin_reviews;
ANALYZE admin_alerts;
